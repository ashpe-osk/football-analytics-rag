from data.users import generate_user_data
import json

if __name__ == "__main__":

    # Here is an example of how to use the generate_users function
    users = generate_user_data(1)[0]
    print("\n\nUser data:")
    print(json.dumps(users, indent=4))
