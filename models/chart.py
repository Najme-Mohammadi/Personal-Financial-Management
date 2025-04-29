from models.db import Database

class Chart:
        def __init__(self, db_name):
            self.db = Database(db_name)

        def get_users_categories(self, user_id):
        # 1. Fetch all categories the user has transactions in.
        # 2. Sum the total amounts for each category.

            query = """
            SELECT category_id, SUM(amount) AS total_amount FROM
            transactions WHERE
            user_id = ?
            GROUP BY category_id;
            """
            result = self.db.fetch_all(query, (user_id,))

        # 3. Return data in a format suitable for charts.
            data = {category_id: total for category_id, total in result}

            return data
        
        def get_all_categories(self, user_id):
            main_categories = [1, 2, 3, 4, 5, 6, 7]
            # 1. Fetch all categories.
            # 2. Sum total amounts spent/earned per category across all users.

            query = """
            SELECT category_id, SUM(amount) AS total_amount, COUNT(DISTINCT user_id) AS user_count
            FROM transactions
            WHERE user_id != ? AND category_id IN (?, ?, ?, ?, ?, ?, ?)
            GROUP BY category_id
           
            """
            # The * operator unpacks the tuple (1, 2, 3, 4, 5, 6, 7), so it spreads the values into separate arguments.
            results = self.db.fetch_all(query, (user_id, *main_categories))
            
            data = []
            
            for category_id, total, user_count in results:
                average = total / user_count if user_count > 0 else 0
                data.append({
                "category_id": category_id,
                "total_amount": total,
                "average_amount": average
                })
            return data 

        def format_chart_data(self, user_id):    
           comparison_data = self.get_all_categories(user_id)
           user_data = self.get_users_categories(user_id)
           chart_data = []
    
           for comparison in comparison_data:
            category_id = comparison["category_id"]
            comparison["user_total"] = user_data.get(category_id, 0)  # get the user's total for this category, default to 0 if not found
            chart_data.append(comparison)
    
           return chart_data
       
        def format_user_chart_data(self, user_id):
            user_data = self.get_users_categories(user_id)

            chart_data = []
            for category_id, total in user_data.items():
               chart_data.append({
                  "category_id": category_id,
                  "total_amount": total
                })

            return chart_data
