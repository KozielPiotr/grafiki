from flask import render_template, flash, redirect, url_for, request
from flask_login import login_user, logout_user, current_user, login_required
from werkzeug.urls import url_parse
from app import app, db
from app.forms import LoginForm, NewUserForm, NewShopForm, UserToShopForm, NewScheduleChoice
from app.models import User, Shop, Personal_schedule
import calendar
import datetime
from datetime import datetime, date


# welcome page
@app.route("/")
@app.route("/index")
@login_required
def index():
    return render_template("index.html", title="Grafiki")


# Login page. Checks if user is logged in and if not redirects to log in  page
@app.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("index"))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user is None or not user.check_password(form.password.data):
            flash("Nieprawidłowa nazwa użytkownika lub hasło")
            return redirect(url_for("index"))
        login_user(user, remember=form.remember_me.data)
        next_page = request.args.get("next")
        if not next_page or url_parse(next_page).netloc !="":
            next_page = url_for("index")
        return redirect(next_page)
    return render_template("login.html", title="Grafiki - logowanie", form=form)


#  Logging out user
@app.route("/logout")
#@login_required
def logout():
    logout_user()
    return redirect(url_for("index"))


#  New user
@app.route("/new-user", methods=["GET", "POST"])
#@login_required
def new_user():
    #if current_user.access_level != "0" and current_user.access_level != "1":
        #flash("Użytkownik nie ma uprawnień do wyświetlenia tej strony")
        #return redirect(url_for("index"))

    form = NewUserForm()
    if form.validate_on_submit():
        user = User(username=form.username.data, access_level=form.access_level.data)
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        flash("Nowy użytkownik zarejestrowany")
        return redirect(url_for("index"))
    return render_template("new_user.html", title="Grafiki - nowy użytkownik", form=form)


# New shop
@app.route("/new-shop", methods=["GET", "POST"])
#@login_required
def new_shop():
    # if current_user.access_level != "0" and current_user.access_level != "1":
        # flash("Użytkownik nie ma uprawnień do wyświetlenia tej strony")
        # return redirect(url_for("index"))

    form = NewShopForm()
    if form.validate_on_submit():
        shop = Shop(shopname=form.shopname.data)
        db.session.add(shop)
        db.session.commit()
        flash("Stworzono nowy sklep")
        return redirect(url_for("index"))
    return render_template("new_shop.html", title="Grafiki - nowy sklep", form=form)


# Assigns user to the shop
@app.route("/shop-user-connect", methods=["GET", "POST"])
#@login_required
def user_to_shop():
    # if current_user.access_level != "0" and current_user.access_level != "1":
        # flash("Użytkownik nie ma uprawnień do wyświetlenia tej strony")
        # return redirect(url_for("index"))

    form = UserToShopForm()
    shop = Shop.query.order_by(Shop.shopname).all()
    user = User.query.order_by(User.username).all()
    users_number = len(user)
    if form.validate_on_submit():
        u = form.user.data
        s = form.shop.data
        already_assigned = s.works
        if u not in already_assigned:
            s.works.append(u)
            db.session.commit()
            flash("Przypisano %s do %s" %(u, s))
        else:
            flash("%s był już przypisany do %s" %(u, s))
        return redirect(url_for("user_to_shop"))
    return render_template("user_to_shop.html", title="Grafiki - przydzielanie użytkownika do sklepu",
                           form=form, user=user, shop=shop, users_number=users_number)


# removes connection between user and shop
@app.route("/remove-user-from-shop", methods=["GET", "POST"])
#@login_required
def remove_from_shop():
    #if (current_user.access_level != "0") and (current_user.access_level != "1"):
        #flash("Użytkownik nie ma uprawnień do wyświetlenia tej strony")
        #return redirect(url_for("index"))

    user = request.args.get("user")
    shop = request.args.get("shop")
    u = User.query.filter_by(username=user).first()
    s = Shop.query.filter_by(shopname=shop).first()
    s.works.remove(u)
    db.session.commit()
    flash("Usunięto %s z %s"%(user, shop))
    return redirect(url_for("user_to_shop"))


@app.route("/new-schedule", methods=["GET", "POST"])
@login_required
def new_schedule():
    if current_user.access_level != "0" and current_user.access_level != "1" and current_user.access_level != "2":
        flash("Użytkownik nie ma uprawnień do wyświetlenia tej strony")
        return redirect(url_for("index"))

    form = NewScheduleChoice()
    u = current_user.workers_shop
    users_shops = []
    for i in u:
        users_shops.append((str(i), str(i)))

    form.shop.choices = users_shops
    if form.validate_on_submit():
        s = form.shop.data
        y = form.year.data
        m = form.month.data
        h = form.hours.data
        i_s = form.in_schedule.data
        return redirect(url_for("create_schedule", year=y, month=m, shop=s, hours=h, i_s=i_s))
    return render_template("new_schedule.html", title="Grafiki - nowy grafik", form=form)


"""
I'm not using calendar module's names for months and days because whole app has to be in polish,
    so the code is little more complicated.
"""
@app.route("/create-schedule/<year>/<month>/<shop>", methods=["GET", "POST"])
@login_required
def create_schedule(year, month, shop):
    if current_user.access_level != "0" and current_user.access_level != "1" and current_user.access_level != "2":
        flash("Użytkownik nie ma uprawnień do wyświetlenia tej strony")
        return redirect(url_for("index"))

    yearn = int(year)
    monthn = int(month)
    month_names = ["Styczeń", "luty", "Marzec", "Kwiecień", "Maj", "Czerwiec", "Lipiec", "Sierpień",
                   "Wrzesień", "Październik", "Listopad", "Grudzień"]
    month_name = month_names[(monthn)-1]
    cal = calendar.Calendar()
    weekday_names = ["Poniedziałek", "Wtorek", "Środa", "Czwartek", "Piątek", "Sobota", "Niedziela"]
    hours = request.args.get("hours")
    i_s = request.args.get("i_s")

    s = Shop.query.filter_by(shopname=shop).first()
    sw = s.works.order_by(User.access_level.asc())
    workers = []
    for worker in sw:
        workers.append(worker)

    # if current user makes schedule, which  shouldn't include himself
    if i_s == "False":
        if current_user in workers:
            workers.remove(current_user)


    return render_template("empty_schedule.html", title="Grafiki - nowy grafik", workers=workers,
                           shop=shop, year=year, mn=month_name, cal=cal, wdn=weekday_names,
                           monthn=monthn, yearn=yearn, hours=hours)


@app.route("/<path:path>")
def static_proxy(path):
    return app.send_static_file(path)


@app.route('/schedule', methods=['POST'])
def transcribe():
    data = request.json
    try:
        for dates in data.items():
            for day in dates:
                for element in day:
                    d = date(int(element["year"]), int(element["month"]), int(element["day"]))
                    worker = element["worker"]
                    b_hour = element["from"]
                    e_hour = element["to"]
                    sum = element["sum"]
                    event = element["event"]
                    workplace = element["workplace"]
                    print(d, worker, b_hour, e_hour, sum, event, workplace)
        return url_for("index")
    except (AttributeError):
        return "Popraw błędy w stworzonym grafiku"