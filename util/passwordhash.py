"""
Helper script to generate bcrypt password hashes for office users.

Usage:
    python generate_password_hashes.py

This will prompt you to enter usernames and passwords, then generate bcrypt hashes.
Copy the hashes into app.py OFFICE_USERS dictionary.
"""

import bcrypt
import getpass

def hash_password(password):
    """Generate bcrypt hash for a password"""
    salt = bcrypt.gensalt(rounds=12)
    hashed = bcrypt.hashpw(password.encode(), salt)
    return hashed.decode()

def main():
    print("=" * 60)
    print("🔐 Bcrypt Password Hash Generator")
    print("=" * 60)
    print("\nThis tool generates bcrypt hashes for office user passwords.")
    print("Copy the hashes into app.py OFFICE_USERS dictionary.\n")
    
    users = {}
    
    while True:
        username = input("Enter username (or 'done' to finish): ").strip()
        
        if username.lower() == 'done':
            break
        
        if not username:
            print("  Username cannot be empty.")
            continue
        
        password = getpass.getpass(f"Enter password for '{username}': ")
        confirm = getpass.getpass("Confirm password: ")
        
        if password != confirm:
            print("  Passwords do not match. Try again.\n")
            continue
        
        if len(password) < 8:
            print("  Password should be at least 8 characters.\n")
            continue
        
        hashed = hash_password(password)
        users[username] = hashed
        print(f"  ✅ Hash generated for '{username}'\n")
    
    # Display results
    print("\n" + "=" * 60)
    print("📋 Password Hashes")
    print("=" * 60)
    print("\nCopy this into app.py OFFICE_USERS:\n")
    
    print("OFFICE_USERS = {")
    for username, hashed in users.items():
        print(f'    "{username}": "{hashed}",')
    print("}")
    
    print("\n" + "=" * 60)
    print("✅ Done! Replace OFFICE_USERS in app.py with the above.")
    print("=" * 60)

if __name__ == "__main__":
    main()