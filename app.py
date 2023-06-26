from flask import Flask, redirect, url_for, request, render_template, flash, session
from flask_session import Session
from itsdangerous import URLSafeTimedSerializer
import os
import pymysql
import smtplib

app = Flask(__name__)
app.secret_key = os.urandom(24)
app.config['SESSION_TYPE'] = 'filesystem'
app.config['SESSION_PERMANENT'] = False
Session(app)
user=os.environ.get('RDS_USERNAME')
db=os.environ.get('RDS_DB_NAME')
password=os.environ.get('RDS_PASSWORD')
host=os.environ.get('RDS_HOSTNAME')
port=os.environ.get('RDS_PORT')
with mysql.connector.connect(host=host,user=user,password=password,port=port,db=db) as conn:
    cursor=conn.cursor(buffered=True)
    cursor.execute("create table if not exists users(username varchar(50) primary key,password varchar(15),email varchar(60))")
    cursor.execute("create table if not exists notes(nid int not null auto_increment primary key,title tinytext,content text,date timestamp default now() on update now(),added_by varchar(50),foreign key(added_by) references users(username))")
    cursor.close()
mydb=mysql.connector.connect(host=host,user=user,password=password,db=db)

#mydb = pymysql.connect(host="localhost",user="root",password="admin",database="cars",autocommit=True)

def create_table():
    try:
        cursor = mydb.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INT AUTO_INCREMENT PRIMARY KEY,
                username VARCHAR(255),
                password VARCHAR(255),
                email VARCHAR(255)
            )
        """)
        mydb.commit()
        print("Table 'users' created successfully")
    except pymysql.Error as e:
        print("Error creating 'users' table:", e)
    finally:
        cursor.close()

def create_table_user_details():
    try:
        cursor = mydb.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_details (
                id INT AUTO_INCREMENT PRIMARY KEY,
                name VARCHAR(255),
                email VARCHAR(255),
                phone VARCHAR(255),
                pickup_date DATE,
                return_date DATE,
                car_type VARCHAR(255),
                num_of_days INT
            )
        """)
        mydb.commit()
        print("Table 'user_details' created successfully")
    except pymysql.Error as e:
        print("Error creating 'user_details' table:", e)
    finally:
        cursor.close()

def insert_data(name, email, phone, pickup_date, return_date, car_type, num_of_days):
    try:
        cursor = mydb.cursor()
        query = "INSERT INTO user_details (name, email, phone, pickup_date, return_date, car_type, num_of_days) " \
                "VALUES (%s, %s, %s, %s, %s, %s, %s)"
        data = (name, email, phone, pickup_date, return_date, car_type, num_of_days)
        cursor.execute(query, data)
        mydb.commit()
        print("Data inserted successfully")
    except pymysql.Error as e:
        print("Error inserting data into 'user_details' table:", e)
    finally:
        cursor.close()

def send_email(recipient, subject, body):
    sender_email = "nagasivakirangajula@gmail.com"
    sender_password = "gowujwbludtwynos"

    message = f"Subject: {subject}\n\n{body}"

    with smtplib.SMTP("smtp.gmail.com", 587) as server:
        server.starttls()
        server.login(sender_email, sender_password)
        server.sendmail(sender_email, recipient, message)

@app.route("/")
def index():
    return render_template('title.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if session.get('user'):
        return redirect(url_for('home'))

    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        cursor = mydb.cursor()
        cursor.execute('SELECT count(*) FROM users WHERE username=%s and password=%s', [username, password])
        count = cursor.fetchone()[0]

        if count == 1:
            session['user'] = username
            return redirect(url_for('home'))
        else:
            flash('Invalid username or password', 'error')
            return redirect(url_for('login'))

    return render_template('login.html')

@app.route('/homepage')
def home():
    if session.get('user'):
        return render_template('home.html')
    else:
        return redirect(url_for('login'))

@app.route('/registration', methods=['GET', 'POST'])
def registration():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        email = request.form['email']
        cursor = mydb.cursor()
        cursor.execute('SELECT count(*) FROM users WHERE username=%s', [username])
        count = cursor.fetchone()[0]
        cursor.execute('SELECT count(*) FROM users WHERE email=%s', [email])
        count1 = cursor.fetchone()[0]
        cursor.close()
        if count == 1:
            flash('Username already in use', 'error')
            return render_template('registration.html')
        elif count1 == 1:
            flash('Email already in use', 'error')
            return render_template('registration.html')
        data = {'username': username, 'password': password, 'email': email}
        serializer = URLSafeTimedSerializer(app.secret_key)
        token = serializer.dumps(data)
        confirm_url = url_for('confirm', token=token, _external=True)
        flash('Confirmation link sent to email', 'success')
        send_email(email, 'Email Confirmation', f"Thanks for signing up Car Rental Company! Please confirm your email by clicking the link: {confirm_url}")

        # Save registration details in the users table
        try:
            cursor = mydb.cursor()
            query = "INSERT INTO users (username, password, email) VALUES (%s, %s, %s)"
            cursor.execute(query, (username, password, email))
            mydb.commit()
            flash('Details registered!', 'success')
            return redirect(url_for('login'))
        except pymysql.Error as e:
            print("Error inserting data into 'users' table:", e)
            flash('An error occurred during registration', 'error')
            return render_template('registration.html')
        finally:
            cursor.close()
    return render_template('registration.html')

@app.route('/confirm/<token>')
def confirm(token):
    try:
        serializer = URLSafeTimedSerializer(app.secret_key)
        data = serializer.loads(token)
    except Exception as e:
        return 'Link Expired. Please register again.'
    else:
        cursor = mydb.cursor()
        username = data['username']
        cursor.execute('SELECT count(*) FROM users WHERE username=%s', [username])
        count = cursor.fetchone()[0]
        if count == 1:
            cursor.close()
            flash('You are already registered!', 'info')
            return redirect(url_for('login'))
        else:
            cursor.execute('INSERT INTO users VALUES (%s, %s, %s)', [data['username'], data['password'], data['email']])
            mydb.commit()
            cursor.close()
            flash('Details registered!', 'success')
            return redirect(url_for('login'))

@app.route('/logout')
def logout():
    if session.get('user'):
        session.pop('user')
        flash('Successfully logged out')
        return redirect(url_for('login'))
    else:
        return redirect(url_for('login'))

@app.route("/rent-car")
def rent_car():
    return render_template('rent_car.html')

@app.route("/user_details", methods=["GET", "POST"])
def user_details():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        phone = request.form['phone']
        pickup_date = request.form['date']
        return_date = request.form['returnDate']
        car_type = request.form['carType']
        num_of_days = request.form['numOfDays']

        # Save user details in the user_details table
        insert_data(name, email, phone, pickup_date, return_date, car_type, num_of_days)

        flash('Car rental details submitted successfully!', 'success')
        return render_template('thank_you.html')

    return render_template('user_details.html')
@app.route("/thank_you", methods=["GET", "POST"])
def thank_you():
    return render_template('thank_you.html')


if __name__ == "__main__":
    create_table()
    create_table_user_details()
    app.run(debug=True)
