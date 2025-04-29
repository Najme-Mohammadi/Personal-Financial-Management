from flask import Blueprint, request, jsonify
from models.db import Database
from models.auth import Users
from models.transaction import Transaction
from middleware.auth import token_required
from models.chart import Chart
from models.dutch import Dutch
import traceback
from extensions import limiter 


auth_bp = Blueprint("auth", __name__, url_prefix="/auth")
dashboard_bp = Blueprint("dashboard", __name__, url_prefix="/dashboard")
dutch_bp = Blueprint("dutch", __name__)

db = Database("file.db")

@auth_bp.route("/register", methods=["POST"])
@limiter.limit("3 per minute")
def register():
    """
    User Registration
    ---
    description: Registers a new user in the system.
    parameters:
      - name: username
        in: body
        type: string
        required: true
        description: The username of the new user.
      - name: email
        in: body
        type: string
        required: true
        description: The email of the new user.
      - name: password
        in: body
        type: string
        required: true
        description: The password for the new user.
    responses:
      201:
        description: User successfully registered and token generated.
        schema:
          type: object
          properties:
            message:
              type: string
              description: The result message.
            token:
              type: string
              description: The generated authentication token for the user.
      400:
        description: Bad Request if any parameter is missing or invalid.
      500:
        description: Internal Server Error if something goes wrong.
    """
    data = request.get_json()
    username = data.get("username")
    email = data.get("email")
    password = data.get("password")

    user = Users()

    try:
        result = user.create_user(username, email, password)
        user_data = user.db.fetch_one(
            "SELECT id FROM users WHERE email = ? OR username = ?", (email, username)
        )

        if not user_data:
            return (
                jsonify({"error": "Failed to retrieve user ID after registration"}),
                500,
            )

        user_id = user_data["id"]
        token = user.generate_token(user_id)
        return jsonify({"message": result["message"], "token": token}), 201

    except ValueError as ve:
        return jsonify({"error": str(ve)}), 400

    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": "Something went wrong", "message": str(e)}), 500
    finally:
      user.db.close()

@auth_bp.route("/login", methods=["POST"])
@limiter.limit("5 per minute")
def login():
    """
    User Login
    ---
    description: Logs in an existing user with their credentials.
    parameters:
      - name: identifier
        in: body
        type: string
        required: true
        description: User's username or email.
      - name: password
        in: body
        type: string
        required: true
        description: The password for the user.
    responses:
      200:
        description: User successfully logged in and token generated.
        schema:
          type: object
          properties:
            message:
              type: string
              description: The result message.
            token:
              type: string
              description: The generated authentication token for the user.
      400:
        description: Bad Request if any parameter is missing or invalid.
      401:
        description: Unauthorized if the credentials are incorrect.
      500:
        description: Internal Server Error if something goes wrong.
    """
    data = request.get_json()
    if not data:
        return jsonify({"error": "Missing the body."})

    identifier = data.get("identifier")
    password = data.get("password")

    if not identifier or not password:
        return jsonify({"error": "Missing identifier or password"}), 400

    user = Users()

    try:

        result = user.login_user(identifier, password)
        user_data = user.db.fetch_one(
            "SELECT id FROM users WHERE email = ? OR username = ?",
            (identifier, identifier),
        )

        if not user_data:
            return jsonify({"error": "Invalid credentials"}), 401

        user_id = user_data["id"]
        token = user.generate_token(user_id)
        return jsonify({"message": result["message"], "token": token}), 200

    except ValueError as ve:
        return jsonify({"error": str(ve)}), 400

    except Exception as e:
        print("Error:", str(e))
        return jsonify({"error": "Something went wrong", "message": str(e)}), 500
    finally:
      user.db.close()
      
@auth_bp.route("/refresh-token", methods=["POST"])
def refresh_token():
    """
    Refresh Token
    ---
    parameters:
      - name: refresh_token
        in: body
        type: string
        required: true
        description: The refresh token to generate a new access token.
    responses:
      200:
        description: Successfully refreshed access token
        schema:
          type: object
          properties:
            access_token:
              type: string
              description: The new access token
      401:
        description: Invalid refresh token or failed verification
        schema:
          type: object
          properties:
            error:
              type: string
              description: Error message
    """
    data = request.get_json()
    refresh_token = data.get("refresh_token")
    user = Users()
    result = user.verify_token(refresh_token, expected_type="refresh")
    
    if not result["valid"]:
        return jsonify({"error": result["error"]}), 401
    
    new_access_token = user.generate_token(result["user_id"], is_refresh=False)
    return jsonify({"access_token": new_access_token}), 200
    
@dashboard_bp.route("/add_transaction", methods=["POST"])
@token_required
def add_transaction(current_user):
    """
    Add Transaction
    ---
    security:
      - bearerAuth: []
    parameters:
      - name: category_id
        in: body
        type: integer
        required: true
        description: The category ID for the transaction.
      - name: amount
        in: body
        type: number
        format: float
        required: true
        description: The amount for the transaction.
      - name: description
        in: body
        type: string
        required: false
        description: A description for the transaction (optional).
      - name: date
        in: body
        type: string
        format: date
        required: false
        description: The date of the transaction (optional).
    responses:
      201:
        description: Successfully created transaction
        schema:
          type: object
          properties:
            transaction_id:
              type: integer
              description: The ID of the newly created transaction.
      400:
        description: Bad request, invalid or missing parameters
        schema:
          type: object
          properties:
            error:
              type: string
              description: Error message
      401:
        description: Unauthorized, token is missing or invalid
        schema:
          type: object
          properties:
            error:
              type: string
              description: Error message
      500:
        description: Internal server error
        schema:
          type: object
          properties:
            error:
              type: string
              description: Error message
            details:
              type: string
              description: Additional details about the error
    """
    if current_user is None:
        return jsonify({"error": "User not found."}), 401
    data = request.get_json()
    user_id = current_user["id"]

    category_id = data.get("category_id")
    amount = data.get("amount")
    description = data.get("description", "")
    date = data.get("date")

    if not category_id or amount is None:
        return jsonify({"error": "Category ID and amount are required"}), 400

    transaction = Transaction()
    try:
        result = transaction.create_transaction(
            user_id, category_id, amount, description, date
        )
        if "error" in result:
            return jsonify(result), 400

        return jsonify(result), 201

    except ValueError as ve:
        return jsonify({"error": str(ve)}), 400

    except Exception as e:
        return jsonify({"error": "Something went wrong.", "details": str(e)}), 500
    finally:
      transaction.db.close()

@dashboard_bp.route("/transactions", methods=["GET"])
@token_required
def get_all_transactions(current_user):
    """
    Get All Transactions
    ---
    security:
      - bearerAuth: []
    responses:
      200:
        description: Successfully fetched all transactions for the user
        schema:
          type: array
          items:
            type: object
            properties:
              transaction_id:
                type: integer
                description: The ID of the transaction
              category_id:
                type: integer
                description: The ID of the category for the transaction
              amount:
                type: number
                format: float
                description: The amount of the transaction
              description:
                type: string
                description: The description of the transaction
              date:
                type: string
                format: date
                description: The date the transaction occurred
      400:
        description: Bad request, invalid user ID
        schema:
          type: object
          properties:
            error:
              type: string
              description: Error message
      401:
        description: Unauthorized, token is missing or invalid
        schema:
          type: object
          properties:
            error:
              type: string
              description: Error message
      500:
        description: Internal server error
        schema:
          type: object
          properties:
            error:
              type: string
              description: Error message
            details:
              type: string
              description: Additional details about the error
    """
    user_id = current_user["id"]

    if not user_id:
        return jsonify({"error": "User does not exist."}), 400

    transaction = Transaction()
    try:
        response = transaction.get_transactions(user_id)  # Fetch all transactions
        return jsonify(response), 200

    except ValueError as ve:
        return jsonify({"error": str(ve)}), 400

    except Exception as e:
        return jsonify({"error": "Something went wrong.", "details": str(e)}), 500
    finally:
      transaction.db.close()

@dashboard_bp.route("/transactions/<int:transaction_id>", methods=["GET"])
@token_required
def get_transaction_by_id(current_user, transaction_id):
    """
    Get Transaction by ID
    ---
    security:
      - bearerAuth: []
    parameters:
      - in: path
        name: transaction_id
        type: integer
        required: true
        description: The ID of the transaction to fetch
    responses:
      200:
        description: Successfully fetched the transaction details
        schema:
          type: object
          properties:
            transaction_id:
              type: integer
              description: The ID of the transaction
            category_id:
              type: integer
              description: The ID of the category for the transaction
            amount:
              type: number
              format: float
              description: The amount of the transaction
            description:
              type: string
              description: The description of the transaction
            date:
              type: string
              format: date
              description: The date the transaction occurred
      400:
        description: Bad request, invalid user ID
        schema:
          type: object
          properties:
            error:
              type: string
              description: Error message
      401:
        description: Unauthorized, token is missing or invalid
        schema:
          type: object
          properties:
            error:
              type: string
              description: Error message
      404:
        description: Transaction not found
        schema:
          type: object
          properties:
            error:
              type: string
              description: Error message
      500:
        description: Internal server error
        schema:
          type: object
          properties:
            error:
              type: string
              description: Error message
            details:
              type: string
              description: Additional details about the error
    """
    user_id = current_user["id"]

    if not user_id:
        return jsonify({"error": "User does not exist."}), 400

    transaction = Transaction()
    try:
        response = transaction.get_transaction_by_id(
            user_id, transaction_id
        )  # Fetch transaction by ID

        if not response:
            return jsonify({"error": "Transaction not found."}), 404

        return jsonify(response), 200

    except ValueError as ve:
        return jsonify({"error": str(ve)}), 400

    except Exception as e:
        print("Error:", str(e))  # Debugging
        return jsonify({"error": "Something went wrong.", "details": str(e)}), 500
    finally:
      transaction.db.close()

@dashboard_bp.route("/update/<int:transaction_id>", methods=["PATCH"])
@token_required
def update_transaction(current_user, transaction_id):
    """
    Update Transaction
    ---
    security:
      - bearerAuth: []
    parameters:
      - in: path
        name: transaction_id
        type: integer
        required: true
        description: The ID of the transaction to update
      - in: body
        name: body
        required: true
        description: The data to update the transaction with
        schema:
          type: object
          properties:
            category_id:
              type: integer
              description: The ID of the category for the transaction
            amount:
              type: number
              format: float
              description: The amount of the transaction
            transaction_type:
              type: string
              description: The type of the transaction (e.g., expense, income)
            description:
              type: string
              description: The description of the transaction
            date:
              type: string
              format: date
              description: The date of the transaction
    responses:
      200:
        description: Successfully updated the transaction
        schema:
          type: object
          properties:
            transaction_id:
              type: integer
              description: The ID of the updated transaction
            category_id:
              type: integer
              description: The ID of the updated category for the transaction
            amount:
              type: number
              format: float
              description: The updated amount of the transaction
            transaction_type:
              type: string
              description: The updated type of the transaction
            description:
              type: string
              description: The updated description of the transaction
            date:
              type: string
              format: date
              description: The updated date of the transaction
      400:
        description: Bad request, invalid data
        schema:
          type: object
          properties:
            error:
              type: string
              description: Error message
      401:
        description: Unauthorized, token is missing or invalid
        schema:
          type: object
          properties:
            error:
              type: string
              description: Error message
      404:
        description: Transaction not found
        schema:
          type: object
          properties:
            error:
              type: string
              description: Error message
      500:
        description: Internal server error
        schema:
          type: object
          properties:
            error:
              type: string
              description: Error message
            message:
              type: string
              description: Additional details about the error
    """
    data = request.get_json()
    category_id = data.get("category_id", None)
    amount = data.get("amount", None)
    transaction_type = data.get("transaction_type", None)
    description = data.get("description", None)
    date = data.get("date", None)

    user_id = current_user["id"]

    if not user_id:
        return jsonify({"error": "User does not exist."}), 400

    transaction = Transaction()

    try:
        result = transaction.update_transaction(
            user_id,
            transaction_id,
            category_id,
            amount,
            transaction_type,
            description,
            date,
        )

        return jsonify(result), 200

    except ValueError as ve:
        return jsonify({"error": str(ve)}), 400

    except Exception as e:
        return jsonify({"error": "Something went wrong.", "message": str(e)}), 500
    finally:
      transaction.db.close()
      
@dashboard_bp.route("/add_category", methods=["POST"])
@token_required
def add_category(current_user):
    """
    Add Category
    ---
    security:
      - bearerAuth: []
    parameters:
      - in: body
        name: body
        required: true
        description: The data to add a new category
        schema:
          type: object
          properties:
            name:
              type: string
              description: The name of the category
            type:
              type: string
              description: The type of the category (e.g., income, expense)
    responses:
      201:
        description: Successfully created the category
        schema:
          type: object
          properties:
            category_id:
              type: integer
              description: The ID of the created category
            name:
              type: string
              description: The name of the created category
            type:
              type: string
              description: The type of the created category
      400:
        description: Bad request, invalid data or missing fields
        schema:
          type: object
          properties:
            error:
              type: string
              description: Error message
      401:
        description: Unauthorized, token is missing or invalid
        schema:
          type: object
          properties:
            error:
              type: string
              description: Error message
      500:
        description: Internal server error
        schema:
          type: object
          properties:
            error:
              type: string
              description: Error message
            message:
              type: string
              description: Additional details about the error
    """
    data = request.get_json()
    name = data.get("name")
    category_type = data.get("type")
    user_id = current_user["id"]

    if not name or not category_type:
        return jsonify({"error": "Name and category type is required."}), 400

    transaction = Transaction()

    try:
        result = transaction.create_category(user_id, name, category_type)
        return jsonify(result), 201

    except ValueError as ve:
        return jsonify({"error": str(ve)}), 400

    except Exception as e:
        return jsonify({"error": "Something went wrong.", "message": str(e)}), 500
    finally:
      transaction.db.close()
      
@dashboard_bp.route("/chart/<chart_type>", methods=["GET"])
@token_required
def display_chart(current_user, chart_type):
    """
    Display Chart Data
    ---
    security:
      - bearerAuth: []
    parameters:
      - in: path
        name: chart_type
        required: true
        description: The type of chart to display. Can be 'compare' or 'user'.
        type: string
        enum:
          - compare
          - user
    responses:
      200:
        description: Successfully retrieved the chart data
        schema:
          type: object
          properties:
            success:
              type: boolean
              description: Indicates whether the request was successful
            data:
              type: array
              items:
                type: object
                description: The chart data
      401:
        description: Unauthorized, invalid or missing token
        schema:
          type: object
          properties:
            success:
              type: boolean
              description: Indicates whether the request was successful
            error:
              type: string
              description: Error message
      500:
        description: Internal server error
        schema:
          type: object
          properties:
            error:
              type: string
              description: Error message with details about the error
    """
    try:
        user_id = current_user.get("id")
        if not user_id:
            return jsonify({"success": False, "error": "Unauthorized"}), 401

        chart = Chart("file.db")

        if chart_type == "compare":
            data = chart.format_chart_data(user_id)
        elif chart_type == "user":
            data = chart.format_user_chart_data(user_id)
        else:
            return jsonify({"success": True, "data": []}), 200

        return jsonify({"success": True, "data": data}), 200

    except Exception as e:
        return jsonify({"error": f"Internal server error: {str(e)}"}), 500
    finally:
      chart.db.close()

@dutch_bp.route("/dutch", methods=["POST"])
@token_required
def create_group(current_user):
    """
    Create a Dutch Group
    ---
    security:
      - bearerAuth: []
    parameters:
      - in: body
        name: body
        description: The group creation request payload
        required: true
        schema:
          type: object
          properties:
            name:
              type: string
              description: The name of the group
            total_amount:
              type: number
              format: float
              description: The total amount for the group
            members:
              type: array
              items:
                type: integer
              description: A list of member IDs
            spent:
              type: object
              description: Dictionary with spending data for each member
          required:
            - name
            - total_amount
            - members
            - spent
    responses:
      201:
        description: Group created successfully
        schema:
          type: object
          properties:
            success:
              type: boolean
              description: Indicates if the creation was successful
            group_id:
              type: integer
              description: The ID of the created group
      400:
        description: Invalid input, missing or incorrect fields
        schema:
          type: object
          properties:
            error:
              type: string
              description: Error message
      500:
        description: Internal server error
        schema:
          type: object
          properties:
            error:
              type: string
              description: Error message with details about the error
    """
    data = request.get_json()
    name = data.get("name")
    total_amount = data.get("total_amount")
    members = data.get("members")
    spent_dict = data.get("spent")
    created_by = current_user["id"]

    # validate inputs
    if (
         not name
        or total_amount is None
        or not isinstance(total_amount, (int, float))
        or not isinstance(members, list)
        or len(members) < 1
        or not isinstance(spent_dict, dict)
    ):
        return (
            jsonify(
                {
                    "error": "Invalid input. Must include name, numeric total_amount, at least one member, and valid spent data."
                }
            ),
            400,
        )

    try:
        dutch = Dutch()
        result = dutch.create_group(name, created_by, members, total_amount, spent_dict)
        if "error" in result:
            return jsonify(result), 400

        return jsonify(result), 201

    except ValueError as ve:
        return jsonify({"error": str(ve)}), 400

    except Exception as e:
        return jsonify({"error": "Something went wrong.", "details": str(e)}), 500
    finally:
      dutch.db.close()

@dutch_bp.route("/dutch", methods=["GET"])
@token_required
def get_all_groups(current_user):
    """
    Get All Dutch Groups for a User
    ---
    security:
      - bearerAuth: []
    responses:
      200:
        description: Successfully fetched all Dutch groups for the user
        schema:
          type: array
          items:
            type: object
            properties:
              id:
                type: integer
                description: The ID of the group
              name:
                type: string
                description: The name of the group
              total_amount:
                type: number
                format: float
                description: The total amount for the group
              created_by:
                type: integer
                description: The user ID of the creator of the group
              members:
                type: array
                items:
                  type: integer
                  description: The IDs of the users in the group
      400:
        description: User does not exist
        schema:
          type: object
          properties:
            error:
              type: string
              description: Error message explaining that the user does not exist
      500:
        description: Internal server error
        schema:
          type: object
          properties:
            error:
              type: string
              description: Error message with details about the error
    """
    user_id = current_user["id"]

    if not user_id:
        return jsonify({"error": "User does not exist."}), 400

    dutch = Dutch()
    try:
        result = dutch.get_all_groups(user_id)
        return jsonify(result), 200

    except ValueError as ve:
        return jsonify({"error": str(ve)}), 400

    except Exception as e:
        return jsonify({"error": "Something went wrong.", "details": str(e)}), 500
    finally:
      dutch.db.close()

@dutch_bp.route("/dutch/<int:group_id>", methods=["GET"])
@token_required
def get_group(user, group_id):
    """
    Get Dutch Group Information and Calculation
    ---
    security:
      - bearerAuth: []
    parameters:
      - in: path
        name: group_id
        type: integer
        required: true
        description: The ID of the Dutch group to retrieve
    responses:
      200:
        description: Successfully retrieved the group information and calculation details
        schema:
          type: object
          properties:
            group:
              type: object
              properties:
                id:
                  type: integer
                  description: The ID of the group
                name:
                  type: string
                  description: The name of the group
                created_by:
                  type: integer
                  description: The user ID of the creator
                total_amount:
                  type: number
                  format: float
                  description: The total amount for the group
                members:
                  type: array
                  items:
                    type: object
                    properties:
                      id:
                        type: integer
                        description: The ID of the member
                      username:
                        type: string
                        description: The username of the member
            calculation:
              type: object
              properties:
                transactions:
                  type: array
                  items:
                    type: object
                    description: A list of transactions related to the group
      404:
        description: Group not found
        schema:
          type: object
          properties:
            error:
              type: string
              description: Error message indicating the group was not found
      500:
        description: Internal server error
        schema:
          type: object
          properties:
            error:
              type: string
              description: Error message with details about the error
    """
    user_id = user["id"]
    dutch = Dutch()
    try:
    # Get group basic info
      group = dutch.get_group_by_id(user_id, group_id)
      if "error" in group:
        return jsonify(group), 404

    # Get members of the group
      members_data = dutch.db.fetch_all(
        """SELECT users.id, users.username 
        FROM group_members 
        JOIN users ON group_members.user_id = users.id 
        WHERE group_members.group_id = ?""",
        (group_id,),
      )
      members = [{"id": m["id"], "username": m["username"]} for m in members_data]

    # Run calculation
      calculation = dutch.calculation(user_id, group_id)

      return (
        jsonify(
            {
                "group": {
                    "id": group["id"],
                    "name": group["name"],
                    "created_by": group["created_by"],
                    "total_amount": group["total_amount"],
                    "members": members,
                },
                "calculation": calculation.get("transactions", []),
            }
        ),
        200,
    )
    finally:
      dutch.db.close()

@dutch_bp.route("/dutch/<int:group_id>", methods=["PATCH"])
@token_required
def update_group(user, group_id):
    """
    Update Dutch Group Information
    ---
    security:
      - bearerAuth: []
    parameters:
      - in: path
        name: group_id
        type: integer
        required: true
        description: The ID of the Dutch group to update
    requestBody:
      description: Group data to update
      required: true
      content:
        application/json:
          schema:
            type: object
            properties:
              name:
                type: string
                description: The updated name of the group
              total_amount:
                type: number
                format: float
                description: The updated total amount for the group
              new_members:
                type: array
                items:
                  type: integer
                description: List of user IDs to be added as new members
              member_spending:
                type: object
                additionalProperties:
                  type: number
                description: A dictionary of member IDs and their spending amounts
    responses:
      200:
        description: Successfully updated the group information
        schema:
          type: object
          properties:
            success:
              type: boolean
              description: Whether the update was successful
            group:
              type: object
              properties:
                id:
                  type: integer
                  description: The ID of the group
                name:
                  type: string
                  description: The name of the group
                total_amount:
                  type: number
                  format: float
                  description: The total amount for the group
                new_members:
                  type: array
                  items:
                    type: integer
                    description: The IDs of the newly added members
      400:
        description: Invalid input data or failed to update the group
        schema:
          type: object
          properties:
            error:
              type: string
              description: Error message explaining why the update failed
      403:
        description: Forbidden, user does not have permission to update the group
        schema:
          type: object
          properties:
            error:
              type: string
              description: Error message explaining why the update was not allowed
      500:
        description: Internal server error
        schema:
          type: object
          properties:
            error:
              type: string
              description: Error message with details about the error
    """
    #here becouse token required send dict we cane only get the id and couse error so we only try to get the id in all our routes
    user_id = user["id"]
    dutch = Dutch()
    data = request.get_json()
    try:
      name = data.get("name")
      total_amount = data.get("total_amount")
      new_members = data.get("new_members")
      member_spending = data.get("member_spending")

      result = dutch.update_group_by_id(
        user_id, group_id, name, total_amount, new_members, member_spending
      )

      if "error" in result:
        return jsonify(result), 400
      
      return jsonify(result), 200
    
    finally:
      dutch.db.close()

@dutch_bp.route("/dutch/<int:group_id>", methods=["DELETE"])
@token_required
def delete_group(user, group_id):
    """
    Delete a Dutch Group
    ---
    security:
      - bearerAuth: []
    parameters:
      - in: path
        name: group_id
        type: integer
        required: true
        description: The ID of the Dutch group to delete
    responses:
      200:
        description: Successfully deleted the group
        schema:
          type: object
          properties:
            success:
              type: boolean
              description: Whether the group was successfully deleted
      403:
        description: Forbidden, user does not have permission to delete the group
        schema:
          type: object
          properties:
            error:
              type: string
              description: Error message explaining why the deletion was not allowed
      500:
        description: Internal server error
        schema:
          type: object
          properties:
            error:
              type: string
              description: Error message with details about the error
    """
    user_id = user["id"]
    dutch = Dutch()
    try: 
      result = dutch.delete_group_by_id(user_id, group_id)

      if "error" in result:
        return jsonify(result), 403
      
      return jsonify(result), 200
    finally:
      dutch.db.close()
