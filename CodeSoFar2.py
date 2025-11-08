import sqlite3
import os
import sys
import smtplib
import random
import re
import string
from cryptography.fernet import Fernet
from difflib import SequenceMatcher


# ============================================
# PASSWORD INPUT WITH ASTERISKS
# ============================================
def input_password(prompt="Enter password: "):
    """Custom password input that shows '*' for each character typed."""
    # VS Code terminal often doesn't support real-time masking
    if os.getenv("TERM_PROGRAM") == "vscode":
        return input(prompt)

    password = ""
    print(prompt, end='', flush=True)
    # Windows
    if os.name == 'nt':
        import msvcrt
        while True:
            ch = msvcrt.getch()
            if ch in {b'\r', b'\n'}:
                print('')
                break
            elif ch == b'\x08':  # Backspace
                if len(password) > 0:
                    password = password[:-1]
                    sys.stdout.write('\b \b')
                    sys.stdout.flush()
            elif ch == b'\x03':  # Ctrl+C
                raise KeyboardInterrupt
            else:
                ch = ch.decode(errors="ignore")
                if ch.isprintable():
                    password += ch
                    sys.stdout.write('*')
                    sys.stdout.flush()
        # macOS / Linux
    else:
        import termios
        import tty
        fd = sys.stdin.fileno()
        old_settings = termios.tcgetattr(fd)
        try:
            tty.setraw(fd)
            while True:
                ch = sys.stdin.read(1)
                if ch in ('\r', '\n'):
                    print('')
                    break
                elif ch == '\x7f':  # Backspace
                    if len(password) > 0:
                        password = password[:-1]
                        sys.stdout.write('\b \b')
                        sys.stdout.flush()
                elif ch == '\x03':  # Ctrl+C
                    raise KeyboardInterrupt
                else:
                    password += ch
                    sys.stdout.write('*')
                    sys.stdout.flush()
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)

    return password

# ============================================
# ENCRYPTION SETUP
# ============================================
KEY_FILE = "key.key"

def generate_key():
    if not os.path.exists(KEY_FILE):
        key = Fernet.generate_key()
        with open(KEY_FILE, "wb") as key_file:
            key_file.write(key)
        print("Encryption key generated and saved.\n")

def load_key():
    if not os.path.exists(KEY_FILE):
        generate_key()
    with open(KEY_FILE, "rb") as key_file:
        return key_file.read()

fernet = Fernet(load_key())

# ============================================
# TWO - FACTOR AUTHENTICATION
# ============================================
def send_email_otp(receiver_email):
    otp = random.randint(100000, 999999)
    message = f"Subject: Your OTP Code\n\nYour OTP is {otp}"
    
    # Login credentials
    sender = "jerripottulu.2025@vitstudent.ac.in"
    password = "zrdw pbum zzgr flcw"  # Use an App Password, not your main password
    
    # Send email
    with smtplib.SMTP("smtp.gmail.com", 587) as server:
        server.starttls()
        server.login(sender, password)
        server.sendmail(sender, receiver_email, message)
    
    return otp
# ============================================
# CHECKING PASSWORD STRENGTH
# ============================================
def check_password_strength(password, username=""):
    """Check if a password is strong and return feedback."""
    strength_criteria = {
        "length": len(password) >= 8,
        "uppercase": re.search(r"[A-Z]", password),
        "lowercase": re.search(r"[a-z]", password),
        "digit": re.search(r"\d", password),
        "special": re.search(r"[!@#$%^&*(),.?\":{}|<>]", password)
    }

    feedback_parts = []

    # --- Similarity check with username ---
    if username:
        # Normalize both
        user_norm = re.sub(r'[^a-z]', '', username.lower())
        pass_norm = re.sub(r'[^a-z]', '', password.lower())

        # Direct substring check
        if user_norm in pass_norm or pass_norm in user_norm:
            feedback_parts.append("Password is too similar to username")
        else:
            # Fuzzy ratio check
            similarity_ratio = SequenceMatcher(None, user_norm, pass_norm).ratio()
            if similarity_ratio >= 0.6:  # 60% similarity threshold
                feedback_parts.append("Password is too similar to username")

    # --- Standard strength checks ---
    if not strength_criteria["length"]:
        feedback_parts.append("at least 8 characters")
    if not strength_criteria["uppercase"]:
        feedback_parts.append("an uppercase letter")
    if not strength_criteria["lowercase"]:
        feedback_parts.append("a lowercase letter")
    if not strength_criteria["digit"]:
        feedback_parts.append("a number")
    if not strength_criteria["special"]:
        feedback_parts.append("a special character (!@#$%^& etc.)")

    # --- Final result ---
    if not feedback_parts:
        return True, "Strong password "
    else:
        return False, "Weak password  - Missing or issue: " + ", ".join(feedback_parts)

# ============================================
# GENERATE A STRONG PASSWORD
# ============================================
def generate_password(username=""):
    """Generate a strong password that meets all criteria and isn't similar to the username."""
    special_chars = "!@#$%^&*()-_=+[]{};:,.<>?"
    all_chars = string.ascii_letters + string.digits + special_chars

    def too_similar(pwd, uname):
        uname_norm = re.sub(r'[^a-z]', '', uname.lower())
        pwd_norm = re.sub(r'[^a-z]', '', pwd.lower())
        if uname_norm in pwd_norm or pwd_norm in uname_norm:
            return True
        return SequenceMatcher(None, uname_norm, pwd_norm).ratio() >= 0.6

    while True:
        # Ensure at least one of each type
        password_chars = [
            random.choice(string.ascii_lowercase),
            random.choice(string.ascii_uppercase),
            random.choice(string.digits),
            random.choice(special_chars)
        ]
        # Fill the rest randomly to reach 12–16 chars
        password_chars += random.choices(all_chars, k=random.randint(8, 12))
        random.shuffle(password_chars)
        password = "".join(password_chars)

        # Check strength and username similarity
        strong, _ = check_password_strength(password, username)
        if strong and not too_similar(password, username):
            return password

# ============================================
# DATABASE SETUP
# ============================================
def init_db():
    conn = sqlite3.connect("password_manager.db")
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS credentials (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            website TEXT NOT NULL,
            username TEXT NOT NULL,
            password TEXT NOT NULL
        )
    ''')
    conn.commit()
    conn.close()

# ============================================
# CRUD OPERATIONS
# ============================================
def add_credential():
    website = input("Enter website name: ")
    username = input("Enter username: ")
    password = input_password("Enter password: ")
    confirm_password = input_password("Confirm your password: ")
    if confirm_password == password:
        is_strong, feedback = check_password_strength(password, username)
        print(feedback)
        if not is_strong:
            while True:
                print("What would you like to do?")
                print("1. Yes, I would like to use this weak password.")
                print("2. No, I would like to use a stronger password.")
                confirm = input("Enter your choice: ")
                
                if confirm == "1":
                    break
                elif confirm == "2":
                    while True:
                        print("What would you like to do?")
                        print("1. I would like to make the password stronger by myself")
                        print("2. I would like you to generate a stronger password for me.")
                        choice = input("Enter your choice: ")
                        if choice == "1":
                            print("Operation cancelled. Please choose a stronger password.")
                            return
                        elif choice == "2":
                            password = generate_password()
                            print("Your password is:", password)
                            break
                        else:
                            print("Invalid choice! Please try again.\n")
                else:
                    print("Invalid choice! Please try again.\n")

        encrypted_password = fernet.encrypt(password.encode())

        conn = sqlite3.connect("password_manager.db")
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO credentials (website, username, password) VALUES (?, ?, ?)",
            (website, username, encrypted_password)
        )
        conn.commit()
        conn.close()
        print("Credential added successfully!\n")
    else:
        print("Passwords do NOT match. Operation Failed.")

def view_credentials():
    conn = sqlite3.connect("password_manager.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM credentials")
    rows = cursor.fetchall()
    conn.close()

    if not rows:
        print("No credentials found.\n")
        return

    print("\nStored Credentials (Decrypted):")
    print("-" * 60)
    for row in rows:
        decrypted_password = fernet.decrypt(row[3]).decode()
        print(f"ID: {row[0]} | Website: {row[1]} | Username: {row[2]} | Password: {decrypted_password}")
    print("-" * 60 + "\n")

def update_credential():
    view_credentials()
    id_to_update = input("Enter the ID of the credential to update: ")

    website = input("Enter new website name: ")
    username = input("Enter new username: ")
    password = input_password("Enter new password: ")
    confirm_password = input_password("Confirm your password: ")
    if confirm_password == password:
        is_strong, feedback = check_password_strength(password, username)
        print(feedback)
        if not is_strong:
            confirm = input("Would you still like to use this weak password? (y/n): ").lower()
            if confirm != 'y':
                print("Operation cancelled. Please choose a stronger password.")
                return
        encrypted_password = fernet.encrypt(password.encode())

        conn = sqlite3.connect("password_manager.db")
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE credentials
            SET website = ?, username = ?, password = ?
            WHERE id = ?
        ''', (website, username, encrypted_password, id_to_update))
        conn.commit()
        conn.close()
        print("Credential updated successfully!\n")
    else:
        print("Passwords do NOT match. Operation Failed.")

def delete_credential():
    view_credentials()
    id_to_delete = input("Enter the ID of the credential to delete: ")

    conn = sqlite3.connect("password_manager.db")
    cursor = conn.cursor()
    cursor.execute("DELETE FROM credentials WHERE id = ?", (id_to_delete,))
    conn.commit()
    conn.close()
    print("Credential deleted successfully!\n")

# ============================================
# MAIN MENU
# ============================================
def main():
    generate_key()
    init_db()
    master_password = "Python123"
    number_of_tries = 0
    while True:
        if number_of_tries == 2:
            while True:
                print("It seems like you have forgotten your password, would you like to reset it?")
                print("1. Yes, I would like to reset my password.")
                print("2. No, I remember my password.")
                print("3. Exit")
                choice = input("Enter your choice: ")

                if choice == '1':
                    receiver = input("Enter your email: ")
                    otp_sent = send_email_otp(receiver)
                    otp_entered = int(input("Enter the OTP sent to your email: "))

                    if otp_entered == otp_sent:
                        entered_master_password = input_password("Enter your new password:")
                        confirm_master_password = input_password("Confirm your password: ")
                        if confirm_master_password == entered_master_password:
                            master_password = entered_master_password
                            print("Password reset successful!")
                            number_of_tries = 0
                            break
                        else:
                            print("Passwords do NOT match. Operation Failed.")
                    else:
                        print("Invalid OTP.")
                elif choice == '2':
                    number_of_tries = 1
                    break
                elif choice == '3':
                    print("Exiting Secure Password Manager. Goodbye!")
                    sys.exit()
                else:
                    print("Invalid choice! Please try again.\n")

        print("========== Secure Password Manager ==========")
        entered_password = input_password("Enter Password:")
        if entered_password == master_password:
            number_of_tries = 0
            while True:
                print("============================================")
                print("1. Add Credential")
                print("2. View Credentials")
                print("3. Update Credential")
                print("4. Delete Credential")
                print("5. Exit")
                choice = input("Enter your choice: ")

                if choice == '1':
                    add_credential()
                elif choice == '2':
                    view_credentials()
                elif choice == '3':
                    update_credential()
                elif choice == '4':
                    delete_credential()
                elif choice == '5':
                    print("Exiting Secure Password Manager. Goodbye!")
                    break
                else:
                    print("Invalid choice! Please try again.\n")
            break
        else:
            number_of_tries+=1
            print("Incorrect Password.")

# ============================================
# RUN PROGRAM
# ============================================
if __name__ == "__main__":
    main()
