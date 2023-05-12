import os
import bcrypt
from flask import Flask, redirect,render_template,request, session,url_for
from flask_sqlalchemy import SQLAlchemy
from flask_login  import UserMixin,LoginManager,login_user,logout_user,current_user,login_required
from flask_wtf import FlaskForm
from wtforms import StringField,PasswordField,SubmitField
from wtforms.validators import InputRequired,Length,ValidationError
from flask_bcrypt import Bcrypt
import datetime
import json
from werkzeug.utils import secure_filename
from werkzeug.datastructures import  FileStorage
import uuid
from flaskwebgui import FlaskUI
import waitress

app=Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI']='sqlite:///database.sqlite3'
app.config['SECRET_KEY']='thisisasecretkey'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS']=False
app.config['UPLOAD_FOLDER']='static/images/'

db=SQLAlchemy()
db.init_app(app)
bcrypt=Bcrypt(app)


login_manager=LoginManager()
login_manager.init_app(app)
login_manager.login_view ="login"


@login_manager.user_loader
def load_user(user_id):
  return User.query.get(int(user_id))

class User(db.Model,UserMixin):
  id=db.Column(db.Integer,primary_key=True)
 
  username=db.Column(db.String(20),unique=True,nullable=False)
  password=db.Column(db.String(80),nullable=False)


class RegisterForm(FlaskForm):
  username=StringField(validators=[InputRequired(),Length(min=4,max=20)],render_kw={"placeholder":"username"})
  password=PasswordField(validators=[InputRequired(),Length(min=4,max=20)],render_kw={"placeholder":"password"})
  submit= SubmitField("Register")

  def valadiate_username(self,username):
    existing_user_username=User.query.filter_by(username=username.data).first()
    if existing_user_username :
      raise ValidationError("User name already exists,choose another")

class loginform(FlaskForm):
  username=StringField(validators=[InputRequired(),Length(min=4,max=20)],render_kw={"placeholder":"username"})
  password=PasswordField(validators=[InputRequired(),Length(min=4,max=20)],render_kw={"placeholder":"password"})
  submit= SubmitField("login")

class Blogs(db.Model):
  __tablename__='Blogs'
  srno=db.Column(db.Integer,autoincrement=True,primary_key=True)
  username=db.Column(db.String,nullable=False)
  blogname=db.Column(db.String,nullable=False)
  description=db.Column(db.String)
  image=db.Column(db.String)
  time=db.Column(db.String)
  

class Followers(db.Model):
    __tablename__='followers'
    serial=db.Column(db.Integer,autoincrement=True,primary_key=True)
    user=db.Column(db.String,db.ForeignKey("user.username", ondelete='CASCADE'))
    followers=db.Column(db.String, server_default='')
    follows=db.Column(db.String, server_default='')

@app.route('/editpost/<int:srno>',methods=["GET","POST"])
def editepost(srno):
  blog=Blogs.query.filter(Blogs.srno==srno).first()
  if request.method=="POST":
    blog.blogname=request.form["bname"]
    blog.description=request.form["bdescription"]
    bimage=request.files["myfile"]
    blog.time=datetime.datetime.now()
    if bimage.filename !='':
      fromat=bimage.filename.split('.')
      f=str(uuid.uuid4())+'.'+str(fromat[-1])
      bimage.save(os.path.join(app.config['UPLOAD_FOLDER'], f))
      blog.image=f
    
    db.session.add(blog)
    db.session.commit()
    return redirect(url_for('dashboard'))
  else:
    return render_template('editpost.html',blog=blog)

@app.route('/',methods=["GET","POST"])
def home():
  return render_template('home.html')

@app.route('/profile/<string:user>',methods=["GET","POST"])
def profile(user):
  usname=user
  blogs=Blogs.query.filter_by(username=usname).all()
  followers=Followers.query.filter_by(user=usname).first()
  no=0
  for i in blogs:
    no+=1
  if followers.followers !='':
    fl=followers.followers.split(',')
    count=len(fl)
  else:
    count=0
  if followers.follows !='':
    f2=followers.follows.split(',')
    following=len(f2)
  else:
    following=0
  
  return render_template('profile.html',blogs=blogs,count=count,following=following,no=no,user=user)


@app.route('/login',methods=["GET","POST"])
def login():
  form=loginform()
  if request.method=="POST":
    user=User.query.filter_by(username=form.username.data).first()
    teddy1=''
    if user:
        if bcrypt.check_password_hash(user.password,form.password.data):
          login_user(user)
          
          return redirect(url_for('dashboard'))
        else :
          return render_template('login.html',form=form,a='alert')
    else:
     return " user not found"
  else:
   return render_template('login.html',form=form)
@app.route('/deletepost/<int:srno>',methods=["GET","POST"])
def deletepost(srno):
  blog=Blogs.query.filter(Blogs.srno==srno).first()
  if blog.image!='':
    os.remove(os.path.join(app.config['UPLOAD_FOLDER'], blog.image))
  db.session.delete(blog)
  db.session.commit()
  return redirect(url_for('dashboard'))
@app.route('/delete',methods=["GET","POST"])
def delete():
  form=loginform()
  user=User.query.filter_by(username=form.username.data).first()
  foll=Followers.query.filter_by(user=form.username.data).first()
  if user:
      if bcrypt.check_password_hash(user.password,form.password.data):
        db.session.delete(user)
        db.session.commit()
        db.session.delete(foll)
        db.session.commit()
        return redirect(url_for('login'))
      else :
         return render_template('deleteuser.html',form=form,a='alert')
  return render_template('deleteuser.html',form=form)


@app.route('/register',methods=["GET","POST"])
def register():
  form=RegisterForm()
  if form.validate_on_submit():
    usdn=User.query.filter_by(username=form.username.data).first()
    if usdn:
      return render_template('register.html',form=form,a='alert')
    hashed_password = bcrypt.generate_password_hash(form.password.data)
    new_user=User(username=form.username.data,password=hashed_password)
    foll=Followers(user=form.username.data,followers='')
    db.session.add(new_user)
    db.session.commit()
    db.session.add(foll)
    db.session.commit()
    return redirect (url_for('login'))
  return render_template('register.html',form=form)

@app.route('/dashboard',methods=["GET","POST"])
@login_required
def dashboard():
  usname=current_user.username
  
  fol=Followers.query.filter(Followers.user==current_user.username).first()
  b=fol.follows
  if b!='':
    b1=b.split(',')
    blogsna=[]
    posts=[]
    blogsna.append(current_user.username)
    for i in b1:
      u=User.query.filter(User.id==int(i)).first()
      blogsna.append(u.username)
    for i in blogsna:
      blogs=Blogs.query.filter_by(username=i).all()
      for j in blogs:
       posts.append(j)
  else:
    b1=''
    posts=[]
    blogs=Blogs.query.filter_by(username=current_user.username).all()
    for i in blogs:
      posts.append(i)
  if request.method=="POST":
    search=request.form["search"]
    search='%'+search+'%'
    users=User.query.filter(User.username.ilike(search)).all()
    return render_template('match.html',users=users,followe=b1)
  posts=sorted(posts, key=lambda post: post.time)
  return render_template('dashboard.html',blogs=posts,follows=b1)

@app.route('/follow/<int:id>',methods=['POST'])
def follow(id):
  if request.method=="POST":
    users=User.query.filter(User.id==id).first()
    follow=Followers.query.filter(Followers.user==users.username).first()
    if follow.followers =='':
      follow.followers=str(current_user.id)
    else:
      follow.followers=follow.followers+','+str(current_user.id)
    self=Followers.query.filter(Followers.user==current_user.username).first()
    if self.follows =='':
      self.follows=str(id)
    else:
      self.follows=self.follows+','+str(id)
    
    db.session.add(follow)
    db.session.flush()
    db.session.commit()
    db.session.add(self)
    db.session.flush()
    db.session.commit()
  return redirect(url_for('dashboard'))

@app.route('/unfollow/<int:id>',methods=['POST'])
def unfollow(id):
  if request.method=="POST":
    users=User.query.filter(User.id==id).first()
    follow=Followers.query.filter(Followers.user==users.username).first()
    follow.followers=follow.followers.strip(','+str(current_user.id))
    self=Followers.query.filter(Followers.user==current_user.username).first()
    self.follows=self.follows.strip(','+str(id))
    
    db.session.add(follow)
    db.session.flush()
    db.session.commit()
    db.session.add(self)
    db.session.flush()
    db.session.commit()
  return redirect(url_for('dashboard'))


@app.route('/logout',methods=["GET","POST"])
@login_required
def logout():
  logout_user()
  return redirect(url_for('login'))

@app.route('/add',methods=["GET","POST"])
@login_required
def add():
  if request.method=="POST":
    bname=request.form["bname"]
    bdesc=request.form["bdescription"]
    bimage=request.files["myfile"]
    if bimage.filename !='':
      fromat=bimage.filename.split('.')
      f=str(uuid.uuid4())+'.'+str(fromat[-1])
      bimage.save(os.path.join(app.config['UPLOAD_FOLDER'], f))
    else:
      f=''
    usname=current_user.username
    ti=datetime.datetime.now()
    tom=Blogs(username=usname,blogname=bname,description=bdesc,image=f,time=ti)
    db.session.add(tom)
    db.session.commit()
    return render_template('addsuccessfull.html')


  return render_template('add.html')
    
def start_flask(**server_kwargs):

    app = server_kwargs.pop("app", None)
    server_kwargs.pop("debug", None)

    try:
        import waitress

        waitress.serve(app, host='0.0.0.0', **server_kwargs)
    except:
        app.run(host='0.0.0.0', **server_kwargs)

if __name__ == '__main__':
    with app.app_context():
     db.create_all()
def saybye():
        print("on_exit bye")

FlaskUI(
        server=start_flask,
        server_kwargs={
            "app": app,
            "port": 5000,
            "threaded": True,
        },
        width=800,
        height=600,
        on_shutdown=saybye,
    ).run()
    
    