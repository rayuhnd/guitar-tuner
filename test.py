import winsound
import mysql.connector
from mysql.connector import Error
from datetime import datetime

winsound.Beep(500, 200)

while True:
    user = input("Please enter User: ").strip()
    password = input("Enter Password: ").strip()

    # Validate username and password inputs
    if not user or not password:
        print("Username and password cannot be empty. Try again!")
        continue

    try:
        # Establish the connection
        connection = mysql.connector.connect(
            user=user,
            password=password,
            database='book_store',
            host='localhost'
        )

        if connection.is_connected():
            print("\nConnection established successfully!")
            break  # Exit the loop once connected

    except Error as err:
        print("Incorrect username or password. Please try again!")

# Create a cursor object
cursor = connection.cursor()


def main_menu():
    """Main menu of the application."""
    while True:
        print("""
=================================================================
___.                  __               __                        
\_ |__   ____   ____ |  | __   _______/  |_  ___________   ____  
 | __ \ /  _ \ /  _ \|  |/ /  /  ___/\   __\/  _ \_  __ \_/ __ \ 
 | \_\ (  <_> |  <_> )    <   \___ \  |  | (  <_> )  | \/\  ___/ 
 |____ /\____/ \____/|__|__\ /_____ > |__|  \____/|__|    \____>
                                                          
==================================================================
         --- Welcome to the BookStore Application ---              
              """)
        print("1. Register")
        print("2. Login")
        print("3. Quit")
        
        choice = input("Choose an option: ")
        if choice == '1':
            register()
        elif choice == '2':
            login()
        elif choice == '3':
            print("Goodbye!")
            break
        else:
            print("Invalid choice. Please try again.")


def register():
    print("\n--- Register ---")
    fname = input("Enter your first name: ")
    lname = input("Enter your last name: ")
    address = input("Enter your address: ")
    city = input("Enter your city: ")
    zip = input("Enter your zip: ")
    phone = input("Enter your phone number: ")
    email = input("Enter your email: ")
    password = input("Enter a password: ")

    try:
        cursor.execute(
            """
            INSERT INTO Members (email, password, fname, lname,
            address, city, zip, phone)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (email, password, fname, lname, address, city, zip, phone)
        )
        connection.commit()

        # Fetch the auto-generated userid
        cursor.execute("SELECT LAST_INSERT_ID()")
        userid = cursor.fetchone()[0]
        print(f"Registration successful! Your User ID is {userid}.\n")
        return userid
    except mysql.connector.Error as err:
        print(f"Error: {err}")


def login():
    """Log in an existing user."""
    print("\n--- Login ---")
    email = input("Email: ")
    password = input("Password: ")

    # Query the database to find the user by email and password
    cursor.execute(
        "SELECT userid, fname, lname, email FROM Members WHERE email = %s AND password = %s", 
        (email, password))
    member = cursor.fetchone()

    if member:
        userid = member[0]  # Extract the userid from
        # the first column of the result
        print(f"Welcome back, {member[1]} {member[2]}!")  
        # Print user's full name (first name, last name)
        member_menu(userid)  # Pass the userid to the member menu
    else:
        print("Invalid email or password.")


def member_menu(userid):
    """Menu for logged-in members."""
    while True:
        print("\n--- Member Menu ---")
        print("1. Browse by Subject")
        print("2. Search by Author/Title")
        print("3. Check Out")
        print("4. Logout")

        choice = input("Choose an option: ")
        if choice == '1':
            browse_by_subject(userid)
        elif choice == '2':
            search_books(userid)
        elif choice == '3':
            check_out(userid)
        elif choice == '4':
            print("Logged out.")
            break
        else:
            print("Invalid choice.")


def browse_by_subject(userid):
    """Browse books by subject."""
    print("\n--- Browse by Subject ---")
    cursor.execute("SELECT DISTINCT subject FROM Books ORDER BY subject")
    subjects = cursor.fetchall()

    for i, subject in enumerate(subjects, 1):
        print(f"{i}. {subject[0]}")

    choice = input("Select a subject by number or press Enter to return: ")
    if choice.isdigit() and 1 <= int(choice) <= len(subjects):
        subject = subjects[int(choice) - 1][0]
        display_books_by_subject(subject, userid)  # Pass userid correctly
    else:
        print("Returning to menu.")


def display_books_by_subject(subject, userid):
    """Display books in a specific subject, two at a time."""
    cursor.execute("SELECT isbn, title, author, price FROM Books WHERE subject = %s", (subject,))
    books = cursor.fetchall()

    if not books:
        print(f"No books found in the subject: {subject}")
        return

    print(f"\nBooks in {subject}:")
    page_size = 2  # Number of books per page
    total_books = len(books)
    current_index = 0

    while current_index < total_books:
        # Display two books at a time
        for i in range(current_index, min(current_index + page_size, total_books)):
            book = books[i]
            print(f"ISBN: {book[0]}, Title: {book[1]}, Author: {book[2]}, Price: {book[3]}")

        # Check if there's more to show
        if current_index + page_size < total_books:
            next_action = input("\nType 'n' for next page, 'b' to go back, or press Enter to enter ISBN: ").strip().lower()
            if next_action == 'n':
                current_index += page_size  # Move to the next page
            elif next_action == 'b' and current_index > 0:
                current_index -= page_size  # Go back to the previous page
            else:
                break  # Exit pagination
        else:
            print("\nEnd of the list.")
            break

    while True:
        isbn = input("\nEnter ISBN to add to Cart or press Enter to return: ")
        if isbn.strip() == "":
            break
        add_to_cart(isbn, userid)


def search_books(userid):
    """Search books by author, title, or go back to member menu."""
    while True:
        print("\n--- Search Books ---")
        print("1. Search by Author")
        print("2. Search by Title")
        print("3. Go back to Member Menu")
        
        choice = input("Enter your option: ").strip()

        if choice == '1':
            search_by_author(userid)
            break  # Exit after performing the search
        elif choice == '2':
            search_by_title(userid)
            break  # Exit after performing the search
        elif choice == '3':
            print("Returning to member menu.")
            break  # Exit to member menu
        else:
            print("Invalid choice. Please try again.")

def display_books_paginated(books):
    """Display books two at a time."""
    if not books:
        print("No books found.")
        return

    page_size = 2  # Number of books per page
    total_books = len(books)
    current_index = 0

    while current_index < total_books:
        # Display two books at a time
        for i in range(current_index, min(current_index + page_size, total_books)):
            book = books[i]
            print(f"ISBN: {book[0]}, Title: {book[1]}, Author: {book[2]}, Price: {book[3]}")

        # Check if there's more to show
        if current_index + page_size < total_books:
            next_action = input("\nType 'n' for next page, 'b' to go back, or press Enter to enter ISBN: ").strip().lower()
            if next_action == 'n':
                current_index += page_size  # Move to the next page
            elif next_action == 'b' and current_index > 0:
                current_index -= page_size  # Go back to the previous page
            else:
                break  # Exit pagination
        else:
            print("\nEnd of the list.")
            break

def search_by_author(userid):
    """Search books by author."""
    author = input("Enter author name or part of it: ").strip()
    cursor.execute("SELECT isbn, title, author, price FROM Books WHERE author LIKE %s COLLATE utf8mb4_general_ci", (f"%{author}%",))
    books = cursor.fetchall()

    print(f"\n{len(books)} books found:")
    display_books_paginated(books)
    add_to_cart_prompt(userid)

def search_by_title(userid):
    """Search books by title."""
    title = input("Enter title or part of the title: ").strip()
    cursor.execute("SELECT isbn, title, author, price FROM Books WHERE title LIKE %s COLLATE utf8mb4_general_ci", (f"%{title}%",))
    books = cursor.fetchall()

    print(f"\n{len(books)} books found:")
    display_books_paginated(books)
    add_to_cart_prompt(userid)


def add_to_cart_prompt(userid):
    """Prompt user to add book to cart."""
    while True:
        isbn = input("\nEnter ISBN to add to Cart or press Enter to return: ").strip()
        if isbn == "":  # Exit to menu
            break
        add_to_cart(isbn, userid)
        
def add_to_cart(isbn, userid):
    """Add a book to the cart."""
    try:
        # Check if the user exists in the Members table
        cursor.execute("SELECT userid FROM Members WHERE userid = %s", (userid,))
        if cursor.fetchone() is None:
            print(f"Error: User ID {userid} does not exist!")
            return

        # Validate ISBN length (should be 10 or 13 characters)
        if len(isbn) not in [10, 13]:
            print("Error: Invalid ISBN length. ISBN must be 10 or 13 characters.")
            return

        # Prompt user for quantity
        quantity = input("Enter quantity: ")
        if not quantity.isdigit() or int(quantity) <= 0:
            print("Quantity must be a positive integer.")
            return

        quantity = int(quantity)

        # Insert or update the cart
        cursor.execute("SELECT * FROM Cart WHERE userid = %s AND isbn = %s", (userid, isbn))
        cart_item = cursor.fetchone()

        # If the book already exists in the cart, update the quantity
        if cart_item:
            cursor.execute("UPDATE Cart SET qty = qty + %s WHERE userid = %s AND isbn = %s", (quantity, userid, isbn))
            print(f"Added {quantity} more copies of the book to your cart!")
        else:
            # If the book does not exist in the cart, insert it
            cursor.execute("INSERT INTO Cart (userid, isbn, qty) VALUES (%s, %s, %s)", (userid, isbn, quantity))
            print(f"Added {quantity} copies of the book to your cart!")

        # Commit the changes to the database
        connection.commit()

    except mysql.connector.Error as err:
        print(f"Error: {err}")



def check_out(userid):
    """Check out books."""
    print("\n--- Check Out ---")
    cursor.execute(
        "SELECT Cart.isbn, Books.title, Books.price, Cart.qty "
        "FROM Cart JOIN Books ON Cart.isbn = Books.isbn WHERE Cart.userid = %s", 
        (userid,)
    )
    cart_items = cursor.fetchall()

    if not cart_items:
        print("Your cart is empty.")
        return

    total = 0
    print("\nInvoice:")
    for item in cart_items:
        isbn, title, price, qty = item
        subtotal = price * qty
        total += subtotal
        print(f"Title: {title}, Price: {price}, Quantity: {qty}, Subtotal: {subtotal}")

    print(f"\nTotal: {total}")
    confirm = input("Proceed to checkout (y/n)? ").lower()

    if confirm == 'y':
        order_date = datetime.now().date()  # Current date
        shipment_address = input("Enter shipping address: ")
        shipment_city = input("Enter shipping city: ")
        shipment_zip = input("Enter shipping ZIP code: ")

        # Validate ZIP code
        if not shipment_zip.isdigit():
            print("Invalid ZIP code.")
            return

        shipment_zip = int(shipment_zip)

        # Generate a unique order number (assuming ono starts from 1 and increments)
        cursor.execute("SELECT MAX(ono) FROM Orders")
        max_ono = cursor.fetchone()[0]
        if max_ono is None:
            max_ono = 0
        new_ono = max_ono + 1

        # Insert the order
        try:
            cursor.execute(
                "INSERT INTO Orders (ono, userid, created, shipAddress, shipCity, shipZip) "
                "VALUES (%s, %s, %s, %s, %s, %s)",
                (new_ono, userid, order_date, shipment_address, shipment_city, shipment_zip)
            )
            connection.commit()
            print(f"Order placed successfully! Your Order Number is {new_ono}.")
        except mysql.connector.Error as err:
            print(f"Error: {err}")
    else:
        print("Checkout cancelled.")


main_menu()

cursor.close()
connection.close()