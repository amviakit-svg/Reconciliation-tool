import os
import sys
import sqlite3

# Ensure backend directory is in path
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'backend'))

try:
    from auth import hash_password, validate_password_strength, generate_secure_password
except ImportError as e:
    print(f"Error importing authentication functions: {e}")
    sys.exit(1)

DB_PATH = 'data/metadata.db'

def main():
    if not os.path.exists(DB_PATH):
        print(f"Error: Database file not found at {DB_PATH}")
        sys.exit(1)

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    try:
        # Find all active admin users
        cursor.execute("SELECT u.id, u.email, u.name, c.name as company_name, c.code as company_code FROM users u LEFT JOIN companies c ON u.company_id = c.id WHERE u.role = 'admin'")
        admins = cursor.fetchall()

        if not admins:
            print("No admin users found in the database.")
            conn.close()
            return

        print("\n=== Available Company Admins ===")
        for idx, admin in enumerate(admins):
            company_info = f"Company: {admin['company_name']} ({admin['company_code']})" if admin['company_name'] else "No Company context (Super Admin/Orphan)"
            print(f"[{idx + 1}] Email: {admin['email']} | Name: {admin['name']} | {company_info}")

        # Choose user
        choice = input("\nSelect the admin ID number to reset (or press Enter to exit): ").strip()
        if not choice:
            print("Exiting.")
            conn.close()
            return

        try:
            choice_idx = int(choice) - 1
            if choice_idx < 0 or choice_idx >= len(admins):
                raise ValueError
        except ValueError:
            print("Invalid choice. Exiting.")
            conn.close()
            return

        selected_admin = admins[choice_idx]
        email = selected_admin['email']
        user_id = selected_admin['id']

        print(f"\nResetting password for: {email}")
        
        # Select password option
        pwd_option = input("Enter 'G' to generate a secure random password, or 'C' to write a custom password (default: G): ").strip().upper()
        
        if pwd_option == 'C':
            while True:
                new_password = input("Enter custom password (must be at least 8 characters, include upper, lower, number, special char): ").strip()
                is_valid, err_msg = validate_password_strength(new_password)
                if is_valid:
                    break
                print(f"Invalid password: {err_msg}. Please try again.")
        else:
            new_password = generate_secure_password(12)

        # Update database
        hashed = hash_password(new_password)
        cursor.execute('''
            UPDATE users 
            SET password_hash = ?, first_login = 1 
            WHERE id = ?
        ''', (hashed, user_id))
        conn.commit()

        print(f"\nPassword successfully updated for {email}!")
        print(f"Temporary Password: {new_password}")
        print("Note: The user will be required to change this password on their first login.")
        
    except Exception as e:
        print(f"\nAn error occurred: {e}")
    finally:
        conn.close()

if __name__ == '__main__':
    main()
