from models.db import Database

class Transaction:

    def __init__(self):
        self.db = Database('file.db')

    def create_category(self, user_id, category_name, category_type):
        if not category_name:
            raise ValueError("Category name cannot be empty.")
        
        if category_type not in ['income', 'expense']:
            raise ValueError("Category type must be either 'income' or 'expense'.")
        
        query = "SELECT * FROM categories WHERE name = ? AND user_id = ?"
        exist_category = self.db.fetch_one(query, (category_name, user_id))

        if exist_category:
             return {"error": "Category with this name already exists."} 

        query = "INSERT INTO  categories(name, type, user_id) VALUES(?, ?, ?)"
        try:
            self.db.execute(query, (category_name, category_type, user_id)) 
            return {"message": "Category created successfuly."} 
         
        except Exception as e:
            return {"error": str(e)}
    
    def create_transaction(self,user_id, category_id, amount, description, date):
        #validate inputs
        if not user_id or not category_id or amount is None:
            raise ValueError("USer ID, category ID and amount are required") 
        
        
        if not isinstance(amount, (int, float)) or amount <= 0:
          raise ValueError("Amount must be positive number.")
        
        if description and len(description) > 255:
            raise ValueError("Description is too long.")
        
        #check if user exists
        user_query = "SELECT id FROM users WHERE id = ?"
        user = self.db.fetch_one(user_query, (user_id,))

        if not user:
            return {"error": "User does not exist."}
        
        
        #check the category
        category_query = "SELECT id, user_id, type FROM categories WHERE id = ? AND (user_id = ? OR user_id IS NULL)"

        category = self.db.fetch_one(category_query, (category_id, user_id))

        if not category:
            return {"error": "category does not exist."}
        
        category_type = category["type"]
        if category_type == "expense" :
            amount = -abs(amount)
        else:
            amount = abs(amount)
        
        query = "INSERT INTO transactions(user_id, category_id, amount, description, date) VALUES (?, ?, ?, ?, COALESCE(?, CURRENT_TIMESTAMP))"

        try:
            self.db.execute(query,(user_id, category_id, amount, description, date))
            return {"message": "Transaction created successfuly"}
        
        except Exception as e:
            return {"error": str(e)}

    def get_transactions(self, user_id):
        #check the user 
        if not user_id:
            return {"error": "User ID is required."}
        
        query = "SELECT * FROM transactions WHERE user_id = ?"
    
        try:
         result = self.db.fetch_all(query, (user_id,))

         transactions = [{
            "id" : row["id"],
            "user_id" : row["user_id"],
            "category_id": row["category_id"],
            "amount": row["amount"],
            "description": row["description"],
            "date": row["date"]

         }
         for row in result
         ]
         return transactions
        
        except Exception as e:
            return {"error": str(e)}
        
    def get_transaction_by_id(self, user_id, transaction_id):
        if not user_id or not transaction_id:
           return {"error": "User ID and Transaction ID are required."}

        query = "SELECT id, user_id, category_id, amount, description, date FROM transactions WHERE id = ? AND user_id = ?"

        try:
           result = self.db.fetch_one(query, (transaction_id, user_id))

           if not result:
              return {"error": "Transaction not found."}

           return {
              "id": result["id"],
              "user_id": result["user_id"],
              "category_id": result["category_id"],
              "amount": result["amount"],
              "description": result["description"],
              "date": result["date"]
            }

        except Exception as e:
           return {"error": str(e)}

        
    def update_transaction(self, user_id, transaction_id, category_id=None, amount=None, transaction_type=None, description=None, date=None):
     if not transaction_id:
        return {"error": "Transaction ID is required."}
    
    # Check if the transaction exists and belongs to the user
     query = "SELECT * FROM transactions WHERE id = ? AND user_id = ?"
     transaction = self.db.fetch_one(query, (transaction_id, user_id))

     if not transaction:
        return {"error": "Transaction not found or unauthorized."}, 404

     category_type = None

     if category_id:
        category_query = "SELECT type FROM categories WHERE id = ? AND (user_id = ? OR user_id IS NULL)"
        category = self.db.fetch_one(category_query, (category_id, user_id))
        if category:
           category_type = category["type"]
        else:
           return{"error": "Category not found or unauthorized."}, 404

     if amount is not None: 
        if not isinstance(amount, (int, float)) or amount <= 0:
            return {"error": "Amount must be a positive number."}
        if category_type == "expense":
            amount = -abs(amount)
        else:
            amount = abs(amount)

     update_fields = []
     values = []

     if category_id:
        update_fields.append("category_id = ?")
        values.append(category_id)

     if amount is not None:
        update_fields.append("amount = ?")
        values.append(amount) 

     if description:
        if len(description) > 255:
            return {"error": "Description is too long."}
        
        update_fields.append("description = ?")
        values.append(description)

     if date:
        update_fields.append("date = ?")
        values.append(date)

     if not update_fields:  
        return {"error": "No fields to update."}

    
     update_query = f"UPDATE transactions SET {', '.join(update_fields)} WHERE id = ? AND user_id = ?"
     values.extend([transaction_id, user_id])

     try:
      self.db.execute(update_query, values)
      return {"message": "Transaction updated successfully."}
     
     except Exception as e:
        return {"error": str(e)}

   
   





