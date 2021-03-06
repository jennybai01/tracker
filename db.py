import sqlite3
import matplotlib.pyplot as plt
import datetime
import pandas as pd
import seaborn as sns
import os # for accessing email address and password (environment variables)
import smtplib
from email.message import EmailMessage
import calendar # for converting datetimes into weekday names i.e. "Monday", "Tuesday", ...
import re #regexp for email validation


def unique_numbers(): # this returns a numpy.ndarray of the unique numbers in the db
    connection = sqlite3.connect("./sqlite/clientdb.sqlite")
    emails = pd.read_sql_query("SELECT DISTINCT phone_number FROM clients_info", connection)
    return emails.phone_number.values

# for number in unique_numbers():
#     print(number)


def tracker_entry(number, mood, stress, sleep, email = "optional"):
    print('RECEIVED.')

    connection = sqlite3.connect("./sqlite/clientdb.sqlite") # creates connection to db
    c = connection.cursor()

    # creating table
    create_db = """
    CREATE TABLE IF NOT EXISTS clients_info (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        phone_number INTEGER,
        email TEXT,
        entry_date DATE,
        mood INTEGER,
        stress INTEGER,
        sleep INTEGER,
        send_email INTEGER
        );
    """
    c.execute(create_db)
    connection.commit()

    existing_numbers_df = pd.read_sql_query("SELECT DISTINCT phone_number FROM clients_info", connection)
    if number in existing_numbers_df["phone_number"].values: # this should be the case if an email parameter is not passed
        select_existing_email = "SELECT DISTINCT email FROM clients_info WHERE phone_number = {}".format(number)
        existing_email_df = pd.read_sql_query(select_existing_email, connection)
        email = existing_email_df.email.values[0]

    check_df = pd.read_sql_query(f"SELECT COUNT(*) as count FROM clients_info WHERE phone_number = {number}", connection)
    if int(check_df["count"].values[0]) % 7 == 6:
        send_email = 1
    else:
        send_email = 0

    # inserting records
    entry = (number, email, datetime.datetime.now(),  mood, stress, sleep, send_email) #UNCOMMENT
    c.execute("INSERT INTO clients_info(phone_number, email, entry_date, mood, stress, sleep, send_email) VALUES (?, ?, ?, ?, ?, ?, ?)", entry) #UNCOMMENT
    connection.commit() #UNCOMMENT

    # figuring out how to use the datetime module
    # print_this_df = pd.read_sql_query("SELECT entry_date FROM clients_info", connection)
    # datetime_str = print_this_df["entry_date"].values[0] # 2020-09-06 22:42:57.879723 (str)
    # datetime_obj = datetime.datetime.strptime(datetime_str, "%Y-%m-%d %H:%M:%S.%f").date() # 2020-09-06 (datetime.date)

    if (send_email == 1): #UNCOMMENT
        # select_info will get the top 7 most recent entries (sorted in ascending order by date) for a specified phone number
        select_info = f"""
        WITH top7 AS (
            SELECT * FROM clients_info
            WHERE phone_number = {number}
            ORDER BY entry_date DESC
            LIMIT 7
        )
        SELECT * FROM
        top7
        ORDER BY entry_date ASC"""

        df = pd.read_sql_query(select_info, connection)
        plot_email = df.email.values[0]
        df["entry_date"] = df["entry_date"].apply(lambda x: datetime.datetime.strptime(x, "%Y-%m-%d %H:%M:%S.%f").date())
        df["entry_date"] = df.entry_date.apply(lambda x: calendar.day_name[x.weekday()])# fix this to represent dates, not times
        sns.set_style("white")
        sns.lineplot(x = "entry_date", y = "mood", data = df, label = "mood", color="cornflowerblue")
        sns.lineplot(x = "entry_date", y = "stress", data = df, label = "stress", color="mediumpurple")
        sns.barplot(x = "entry_date", y = "sleep", data = df, label = "sleep", color="lavender")
        font = {"fontname": "DejaVu Sans"}
        plt.title("Your Mood, Stress and Sleep This Week", fontsize = 18, fontweight = "bold")
        plt.ylabel("Mood, stress & sleep", **font)
        plt.xlabel("Date", **font)
        #plt.show() # DEBUG
        plt.savefig(r"./client_analysis/{}_sms_plot.png".format(number))


        email_address = os.getenv("EMAIL_USER")
        email_pw= os.getenv("EMAIL_PASS")

        msg = EmailMessage()
        msg["Subject"] = "Your Mood, Stress & Sleep Data For the Week!"
        msg["From"] = email_address
        msg["To"] = plot_email
        #msg.set_content("content")

        with open(r"./client_analysis/{}_sms_plot.png".format(number), "rb") as f:
            file_data = f.read()

        msg.add_attachment(file_data, maintype="image", subtype="png", filename = "This week's data!")

        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
            smtp.login(email_address, email_pw)
            smtp.send_message(msg)

