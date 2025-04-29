from models.db import Database
from models.auth import Users

class Dutch:
    def __init__(self):
        self.db = Database("file.db")

    def create_group(self, name, created_by, members, total_amount, spent_dict=None):
        if not name or not created_by or not members or len(members) < 1 or not total_amount or not spent_dict:
            raise ValueError("Invalid data. A group must have a name, at least 1 member, and a total expense.")

        user = Users()
        added_members = []

        # Get user_id for each username in members
        for username in members:
            user_data = user.db.fetch_one("SELECT id FROM users WHERE username = ?", (username,))
            if user_data:
                added_members.append({"username": username, "user_id": user_data["id"]})
            else:
                return {"error": f"User '{username}' not found."}

        # Add creator if not already in the list
        creator_username = user.find_username_by_id(created_by)
        
        if creator_username not in spent_dict:
            raise ValueError("Creator's spent amount must be provided in spent_dict.")
        added_members.append({"username": creator_username, "user_id": created_by})

        # Validate total spending
        total_spent = sum(spent_dict.values())
        if total_spent != total_amount:
            return {"error": "Total amount and individual contributions do not match."}
        
        existing_group = self.db.fetch_one(
           "SELECT id FROM groups WHERE name = ? AND created_by = ?",
            (name, created_by)
        )

        if existing_group:
            return {"error": "You already have a group with this name."}
        try:
            # Insert group
            insert_group_query = """
                INSERT INTO groups (name, created_by, total_amount, member_count)
                VALUES (?, ?, ?, ?)
            """
            cursor = self.db.execute(insert_group_query, (name, created_by, total_amount, len(added_members)))
            if cursor is None:
                return {"error": "Failed to insert group."}

            group_id = cursor.lastrowid

            # Insert group members and transactions
            for member in added_members:
                spent = spent_dict.get(member["username"], 0)
                
                self.db.execute(
                    "INSERT INTO group_members (group_id, user_id, amount_spent) VALUES (?, ?, ?)",
                    (group_id, member["user_id"], spent)
                )

                self.db.execute(
                    "INSERT INTO group_transactions (group_id, user_id, amount_spent) VALUES (?, ?, ?)",
                    (group_id, member["user_id"], spent)
                )
            
            self.calculation(created_by, group_id)
           


            return {"message": "Group created successfully", "group_id": group_id}

        except Exception as e:
            return {"error": "Failed to create group", "details": str(e)}
   
    def get_all_groups(self, user_id):
        if not user_id:
            return {"error": "The user not found."}
        
        query = "SELECT * FROM groups WHERE created_by = ?"
        rows = self.db.fetch_all(query, (user_id,))
        response = [dict(row) for row in rows]

        return response

    def get_group_by_id(self, user_id, group_id):
        if not user_id:
            return {"error": "The user not found."}
        
        query = "SELECT * FROM groups WHERE id = ?"
        response = self.db.fetch_one(query, (group_id,))
        
        if not response:
            return{"error": "Group not found."}
        return response

    def update_group_by_id(self, user_id, group_id, name=None, total_amount=None, new_members=None, member_spending=None):
        if not user_id:
            return {"error": "The user not found."}
        
        query = "SELECT * FROM groups WHERE id = ? AND created_by = ?"
        group = self.db.fetch_one(query, (group_id, user_id))
        
        if not group:
            return{"error": "Group not found or you don't have permission to update it."}
        
        update_fields = []
        update_values = []
        total_changed = False

        if name:
            update_fields.append("name = ?")
            update_values.append(name)

        if total_amount is not None and total_amount != group["total_amount"]:
            update_fields.append("total_amount = ?")
            update_values.append(total_amount)
            total_changed = True
        
        if update_fields:
            query = f"UPDATE groups SET {', '.join(update_fields)} WHERE id = ?"
            self.db.execute(query, (*update_values, group_id))
            
        failed_members = []
        added_members = []
        
        if new_members:
            user = Users()
            for member in new_members:
                if not isinstance(member, dict) or "username" not in member:
                    failed_members.append(str(member))
                    continue
                
                username = member.get["username"]
                amount_spent = member.get("spent", 0)
                
                user_data = user.db.fetch_one("SELECT id FROM users WHERE username = ?", (username,))
                if not user_data:
                    failed_members.append(username)
                    continue
                
                member_id = user_data["id"]
                
                existing_member = self.db.fetch_one("SELECT * FROM group_members WHERE group_id = ? AND user_id = ?",
                (group_id, member_id)
                 )
                if not existing_member:
                    self.db.execute(
                        "INSERT INTO group_members (group_id, user_id) VALUES (?, ?)",
                        (group_id, member_id))
                    added_members.append(username)
                
                    self.db.execute(
                       "INSERT INTO group_transactions (group_id, user_id, amount_spent) VALUES (?, ?, ?)",
                        (group_id, member_id, amount_spent)
            )
                    
        response = {"message": "Group updated successfully."}
        if added_members:
           response["new_members_added"] = added_members
        if failed_members:
            response["failed_to_add"] = failed_members
            
        if total_changed or added_members:
            #we select from transaction the sum becouse in groups table we are try to change it and it consider the uodate amount.
            total_spent = self.db.fetch_one(
                "SELECT SUM(amount) as total FROM group_transactions WHERE group_id = ?",
                (group_id,)
            )["total"]
            # for small differences
            if total_spent != total_amount:
                return {
                    "error": "Please update spending, its more or less than current total."
                }
            try:
                
               result = self.calculation(user_id, group_id)
               response["recaculated"] = True
               response ["new_transactions"] = result.get("transaction", [])
               
            except Exception as e:
                response["recalculated"] = False
                response["calculation_error"] = str(e)
            
        return response
    
    def delete_group_by_id(self, user_id, group_id):
        if not user_id:
            return {"error": "User not found."}
        
        query = "SELECT * FROM groups WHERE id = ? AND created_by = ?"
        group = self.db.fetch_one(query, (group_id, user_id))

        if not group:
            return {"error": "Group not found or you dont have permission to delete it."}
        
        delete_query = "DELETE FROM groups WHERE id = ? AND created_by = ?"

        self.db.execute(delete_query, (group_id, user_id))
        return {"message": "Group deleted successfully."}
    
    def calculation(self, user_id, group_id):
    # Step 1: Verify the group exists and the user has access
        group = self.db.fetch_one("SELECT * FROM groups WHERE id = ? AND created_by = ?", (group_id, user_id))
        if not group:
            return {"error": "Group not found or you don't have permission."}

        total_amount = group["total_amount"]
    # Step 2: Fetch all group member IDs
        members = self.db.fetch_all("SELECT user_id, amount_spent FROM group_members WHERE group_id = ?", (group_id,))
        
        if not members or len(members) < 2:
            return {"error": "A minimum of 2 members is required for calculation."}

        member_ids = [member["user_id"] for member in members]
                
        per_person_share = total_amount / len(member_ids)
    # Step 3: Initialize balances
        balances = []
        for member in members:
            user_id = member["user_id"]
            spent_data = self.db.fetch_one(
              "SELECT amount_spent FROM group_transactions WHERE group_id = ? AND user_id = ?",
               (group_id, user_id)
            )
            paid = spent_data["amount_spent"] if spent_data else 0
           
            balance = round(paid - per_person_share, 2)
           
            balances.append({
            "user_id": user_id,
            "paid": paid,
            "balance": balance 
        })
    # Step 4: Separate debtors and creditors
        debtors = [b for b in balances if b["balance"] < 0]
        creditors = [b for b in balances if b["balance"] > 0]

    # Step 5: Match payers (debtors) with those who should receive (creditors)
        transactions = []
                
        for debtor in debtors:
         amount_to_pay = -debtor["balance"]
         for creditor in creditors:
            if amount_to_pay == 0:
                break
            if creditor["balance"] <= 0:
                continue

            amount = min(amount_to_pay, creditor["balance"])
            transactions.append({
                "from_user": debtor["user_id"],
                "to_user": creditor["user_id"],
                "amount": round(amount, 2)
            })

            amount_to_pay -= amount
            creditor["balance"] -= amount
    # Step 6: (Optional cleanup) Remove previous transactions with from_user set
        self.db.execute(
           "DELETE FROM group_transactions WHERE group_id = ? AND from_user IS NOT NULL",
        (group_id,)
        )

    # Step 7: Insert new calculated transactions into the database
        for tx in transactions:
           self.db.execute(
            "INSERT INTO group_transactions (group_id, from_user, to_user, amount) VALUES (?, ?, ?, ?)",
            (group_id, tx["from_user"], tx["to_user"], tx["amount"])
        )
        return {
        "message": "Calculation completed successfully.",
        "transactions": transactions
    }

    