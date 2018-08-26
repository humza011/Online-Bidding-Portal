import os
from flask import Flask, render_template, flash, request, redirect, url_for, session, logging
import sqlite3 
from wtforms import Form, StringField, IntegerField, TextAreaField, PasswordField, validators
from flask_wtf.file import FileField, FileRequired, FileAllowed
from wtforms.validators import DataRequired,NumberRange
from passlib.hash import sha256_crypt 
from functools import wraps 
from flask_wtf import FlaskForm
from werkzeug.utils import secure_filename
from datetime import datetime
from datetime import timedelta

app = Flask(__name__)


# location where file uploads will be stored
UPLOAD_FOLDER = './static/uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

#connecting database
conn = sqlite3.connect('onbid.db', check_same_thread = False)
c = conn.cursor()

#creating database table
def create_table():
    c.execute('CREATE TABLE IF NOT EXISTS user(uid INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL,email TEXT NOT NULL,username TEXT NOT NULL,password TEXT NOT NULL)')
    c.execute('CREATE TABLE IF NOT EXISTS product(pid INTEGER PRIMARY KEY AUTOINCREMENT ,pname TEXT NOT NULL,pimg TEXT NOT NULL,pdes TEXT NOT NULL,price INTEGER NOT NULL, seller TEXT NOT NULL, uploadtime TEXT NOT NULL, expire TEXT NOT NULL )')
    c.execute('CREATE TABLE IF NOT EXISTS bidinfo(bid INTEGER PRIMARY KEY AUTOINCREMENT ,buyername TEXT NOT NULL, bidprice INTEGER NOT NULL,proname TEXT NOT NULL)')

create_table()


#on logo click
@app.route('/')
def index():
	return render_template('home.html')


#about
@app.route('/about')
def about():
	return render_template('about.html')



#registeration class
class RegisterForm(Form):
	name= StringField('Name',validators=[validators.DataRequired(),validators.Length(min=4, max=15)])
	email = StringField('Email Address',validators=[validators.DataRequired(),validators.Length(max=50),validators.Email()])
	username = StringField('Username',validators=[validators.DataRequired(),validators.Length(min=5, max=50)])
	password = PasswordField('Password',[
		validators.DataRequired(),
		validators.EqualTo('confirm', message='Passwords do not match')
		])
	confirm = PasswordField('Confirm Password')

#user registeration
@app.route('/register', methods = ['GET','POST'])
def register():
	form = RegisterForm(request.form)
	if request.method =='POST' and form.validate():
		name = form.name.data
		email = form.email.data
		username = form.username.data
		password = sha256_crypt.encrypt(str(form.password.data))
	
		c = conn.cursor()
	
		c.execute("INSERT INTO user(name,email,username,password) VALUES(?,?,?,?)",(name,email,username,password))
	
		conn.commit()
	
		c.close()
		flash('You have been registered,login to continue !','success')
		return redirect(url_for('login'))
		
	
	return render_template('register.html', form=form)

class LoginForm(Form):
    username = StringField('Username',validators=[validators.DataRequired(),validators.Length(min=5, max=50)])
    password_candidate = PasswordField('Password',validators=[validators.DataRequired()])



#for login
@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm(request.form)
    
    if request.method == 'POST' and form.validate():
        # Get Form Fields
        username = form.username.data
        password_candidate = form.password_candidate.data
        #username = request.form['username']
        
        #password_candidate = request.form['password']

        # Create cursor
        c = conn.cursor()

        # Get user by username
        result = c.execute("SELECT * FROM user WHERE username = ?", [username])

        if result > 0:
            # Get stored hash
            data = c.fetchone()
            password = data[4]

            # Compare Passwords
            if sha256_crypt.verify(password_candidate, password):
                # Passed
                session['logged_in'] = True
                session['username'] = username

                flash('You are now logged in', 'success')
                return redirect(url_for('dashboard'))
            else:
                error = 'Invalid login'
                return render_template('login.html',error=error ,form=form)
            # Close connection
            c.close()

        else:
            flash('Oops, we couldnt find you in our database. Please Register !','danger')
            return render_template('register.html')

    return render_template('login.html',form=form)



# Check if user logged in
def is_logged_in(f):
    @wraps(f)
    def wrap(*args, **kwargs):
        if 'logged_in' in session:
            return f(*args, **kwargs)
        else:
            flash('Unauthorized, Please login', 'danger')
            return redirect(url_for('login'))
    return wrap

#logout
@app.route('/logout')
@is_logged_in
def logout():
	session.clear()
	flash('You have been logged out','success')
	return redirect(url_for('login'))


#dashboard
@app.route('/dashboard')
@is_logged_in
def dashboard():
	return render_template('dashboard.html')


def flash_errors(form):
    for field, errors in form.errors.items():
        for error in errors:
            flash(u"Error in the %s field - %s" % (
                getattr(form, field).label.text,
                error
            ), 'danger')


class PhotoForm(FlaskForm):
    
    pname = StringField('Product Name', validators=[DataRequired()])
    photo = FileField('Photo', validators=[
        FileRequired(),
        FileAllowed(['jpg', 'png', 'Images only!'])
    ])
    description = StringField('Description', validators=[DataRequired()])
    price = IntegerField('Price', validators=[DataRequired()])


@app.route('/photo-upload', methods=['GET', 'POST'])
@is_logged_in
def photo_upload():
    photoform = PhotoForm()

    if request.method == 'POST' and photoform.validate_on_submit():

        pname = photoform.pname.data
        photo = photoform.photo.data # we could also use request.files['photo']
        description = photoform.description.data
        price = photoform.price.data
        filename = secure_filename(photo.filename)
        
        photo.save(os.path.join(
            app.config['UPLOAD_FOLDER'], filename
        ))
        imgsrc = os.path.join(app.config['UPLOAD_FOLDER'],filename)
        print filename
        print imgsrc
        uptime = datetime.now()
        print uptime
        expire = datetime.now() + timedelta(days=7)
        print expire
        c = conn.cursor()
        #c.execute('CREATE TABLE IF NOT EXISTS product(pid INT AUTO INCREMENT PRIMARY KEY ,pname TEXT ,pimg TEXT ,pdes TEXT ,price INT)')
        
        c.execute("INSERT INTO product(pname,pimg,pdes,price,seller,uploadtime,expire) VALUES(?,?,?,?,?,?,?)",(pname,imgsrc,description,price,session['username'],uptime,expire))
    
        conn.commit()
    
        c.close()
        

        flash('Product Uploaded Successfully !','success')
        return redirect(url_for('dashboard'))
    flash_errors(photoform)
    return render_template('photo_upload.html', form=photoform)




@app.route('/viewproduct')
def showproduct():

    c = conn.cursor()

    # Get articles
    result = c.execute("SELECT * FROM product")
    print result
    products = c.fetchall()
    print products

    if result > 0:
        return render_template('allproduct.html', products=products)
    else:
        msg = 'No Product Found'
        return render_template('allproduct.html', msg=msg)
    # Close connection
    cur.close()


@app.route('/products')
def viewproduct():
    c = conn.cursor()

    # Get articles
    result = c.execute("SELECT * FROM product")
    print result
    products = c.fetchall()
    print products
    if result > 0:
        return render_template('product.html', products=products)
    else:
        msg = 'No Product Found'
        return render_template('product.html', msg=msg)
    # Close connection
    cur.close()


@app.route('/placebid/<string:pid>')
def placebid(pid):

    c = conn.cursor()

    result = c.execute("SELECT * FROM product WHERE pid = ?",[pid])

    product = c.fetchone()

    proname = product[1]

    sellername = product[5]

    res = c.execute("SELECT * FROM bidinfo WHERE proname = ?",[proname])

    print 'Product Detail', proname

    return render_template('placebid.html',product=product,pid=pid,sellername=sellername)


#rotue to proceed bidding
@app.route('/bidproduct/<string:pid>')
def bidproduct(pid):

    c= conn.cursor()

    result = c.execute("SELECT * FROM product WHERE pid = ?",[pid])

    if result > 0:


        product = c.fetchone()

        print product

        proname = product[1]

        print proname

        startprice = product[4]

        print startprice
        
        if startprice <1000:

            bidprice = startprice+10

            print bidprice

        else:

            bidprice = startprice + 100

            print bidprice

        c.execute("INSERT INTO bidinfo(bidprice,buyername,proname) VALUES(?,?,?) ",(bidprice,session['username'],proname))
        pbid = c.execute("SELECT * FROM bidinfo WHERE proname = ?",[proname])
        if pbid > 0:
            c.execute("UPDATE product SET price = ? WHERE pid = ?",(bidprice,pid))
            conn.commit()
            
            c.close()
                

            flash('Bid Placed Successfully !','success')
            return redirect(url_for('dashboard'))
    
        else:
                
            pbid = c.execute("SELECT * FROM bidinfo WHERE proname = ?",(proname))
            conn.commit()
            c.close()
            flash('Failed to place bid for the product !')
            return render_template('dashboard')

@app.route('/bidstatus')
def bidstatus():
    c = conn.cursor()

    # Get articles
    result = c.execute("SELECT * FROM bidinfo")
    print result
    bidres = c.fetchall()
    print bidres
    if result > 0:
        return render_template('bidstatus.html', bidres=bidres)
    else:
        msg = 'No Product Found'
        return render_template('bidstatus.html', msg=msg)
    # Close connection
    cur.close()

if __name__ == '__main__':
	app.secret_key='lifeis123'
   	app.run(debug = True)