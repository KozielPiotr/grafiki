"""
Routes for whole project. Each function is described when it occurs.
"""
#-*- coding: utf-8 -*-
# pylint: disable=no-member

import calendar
from datetime import date, datetime
from flask import render_template, flash, redirect, url_for, request, jsonify
from flask_login import login_user, logout_user, current_user, login_required
from werkzeug.urls import url_parse
from app import app, db
from app.forms import LoginForm, NewUserForm, NewShopForm, UserToShopForm, NewScheduleForm,\
    BillingPeriod
from app.models import User, Shop, Billing_period, Personal_schedule, Schedule


# prepers dict with data to show schedule for previous month
def prev_schedule(month, year, month_names, cal, workplace):
    """
    Makes dictionary with all data needed to create template that shows existing schedule
    :param month: month of schedule
    :param year: year of schedule
    :param month_names: names of month in apps language
    :param cal: calendar module
    :param workplace: workplace for wchich schedule has to be create
    :return: dictionary with all needed data
    """
    if month == 1:
        prev_month = 12
        prev_year = year - 1
    else:
        prev_month = month - 1
        prev_year = year
    prev_month_name = month_names[prev_month - 1]

    try:
        prev_month_last_version = Schedule.query.filter_by(year=prev_year, month=prev_month, workplace=workplace,
                                                           accepted=True).order_by(Schedule.version.desc()).first().\
                                                                                   version
        prev_month_shd = Schedule.query.filter_by(year=prev_year, month=prev_month, workplace=workplace,
                                                  version=prev_month_last_version).first()
    except AttributeError:
        prev_month_shd = None

    if prev_month_shd is not None:
        prev_schd_id = prev_month_shd.id
        prev_workers = []
        for pers_schedule in prev_month_shd.ind:
            if str(pers_schedule.worker).replace(" ", "_") not in prev_workers:
                prev_workers.append(str(pers_schedule.worker).replace(" ", "_"))

        prev_hours = prev_month_shd.hrs_to_work
        prev_shdict = {}
        workers_hours = {}
        for worker in prev_workers:
            worker_hours = 0
            for p_schedule in prev_month_shd.ind:
                if p_schedule.worker == str(worker).replace("_", " "):
                    worker_hours += p_schedule.hours_sum
                workers_hours[worker] = worker_hours

        for worker in prev_workers:
            for day in cal.itermonthdays(prev_year, prev_month):
                if day > 0:
                    begin = Personal_schedule.query.filter_by(date=datetime(prev_year, prev_month, day),
                                                              includes_id=prev_schd_id,
                                                              worker=worker.replace("_", " ")).first().begin_hour
                    end = Personal_schedule.query.filter_by(date=datetime(prev_year, prev_month, day),
                                                            includes_id=prev_schd_id,
                                                            worker=worker.replace("_", " ")).first().end_hour
                    event = Personal_schedule.query.filter_by(date=datetime(prev_year, prev_month, day),
                                                              includes_id=prev_schd_id,
                                                              worker=worker.replace("_", " ")).first().event
                    h_sum = Personal_schedule.query.filter_by(date=datetime(prev_year, prev_month, day),
                                                              includes_id=prev_schd_id,
                                                              worker=worker.replace("_", " ")).first().hours_sum
                    billing_week = Personal_schedule.query.filter_by(date=datetime(prev_year, prev_month, day),
                                                                     includes_id=prev_schd_id,
                                                                     worker=worker.replace("_",
                                                                                           " ")).first().billing_week

                    prev_shdict["begin-%s-%d-%02d-%02d" % (worker, prev_year, prev_month, day)] = begin
                    prev_shdict["end-%s-%d-%02d-%02d" % (worker, prev_year, prev_month, day)] = end
                    prev_shdict["event-%s-%d-%02d-%02d" % (worker, prev_year, prev_month, day)] = event
                    prev_shdict["sum-%s-%d-%02d-%02d" % (worker, prev_year, prev_month, day)] = h_sum
                    prev_shdict["billing-week-%s-%d-%02d-%02d" % (worker, prev_year, prev_month, day)] = billing_week
    else:
        prev_shdict = None
        prev_hours = None
        prev_workers = None
        workers_hours = None
    prev = {"prev_shdict": prev_shdict, "hours": prev_hours, "workers": prev_workers, "workers_hours": workers_hours,
            "year": prev_year, "month": prev_month, "month_name": prev_month_name}
    return prev


# prepares list of schedules aviable for current user to accept or modify
def list_of_schedules_acc_mod(mod_acc):
    """
    Prepares list of schedules aviable for current user to accept or modify.
    :param mod_acc: Defines if function looks for accepted or unaccepted schedules
    :return: list of schedules that match to 'mod_acc' criteria
    """
    schedules = []
    for schedule in Schedule.query.filter_by(accepted=mod_acc).order_by(Schedule.workplace, Schedule.year,
                                                                        Schedule.month, Schedule.version).all():
        for assigned_workplaces in current_user.workers_shop:
            if str(schedule.workplace) == str(assigned_workplaces):
                schedules.append(schedule)

    number_of_schedules = len(schedules)
    schedules_list = {"schedules": schedules, "nos": number_of_schedules}

    return schedules_list


# main page
@app.route("/")
@app.route("/index")
@login_required
def index():
    """
    Main page.
    """
    return render_template("index.html", title="Grafiki")


@app.route("/test", methods=["GET", "POST"])
def test():
    """
    Test route. Needs to be removed in final version.
    """
    queries = []
    months = Schedule.query.filter_by(month=11)
    places = Schedule.query.filter_by(workplace="Sklep 1")
    for month in months:
        if month in places:
            queries.append(month.name)
    print(queries)
    return "%s"


# Login page. Checks if user is logged in and if not redirects to log in  page
@app.route("/login", methods=["GET", "POST"])
def login():
    """
    Logs user in.
    """
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
        if not next_page or url_parse(next_page).netloc != "":
            next_page = url_for("index")
        return redirect(next_page)
    return render_template("login.html", title="Grafiki - logowanie", form=form)


#  Logging out user
@app.route("/logout")
@login_required
def logout():
    """
    Logs out current user.
    """
    logout_user()
    return redirect(url_for("index"))


#  New user
@app.route("/new-user", methods=["GET", "POST"])
@login_required
def new_user():
    """
    Adds new user to database.
    """
    if current_user.access_level != "0" and current_user.access_level != "1":
        flash("Użytkownik nie ma uprawnień do wyświetlenia tej strony")
        return redirect(url_for("index"))

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
@login_required
def new_shop():
    """
    Adds new workplace to database.
    """
    if current_user.access_level != "0" and current_user.access_level != "1":
        flash("Użytkownik nie ma uprawnień do wyświetlenia tej strony")
        return redirect(url_for("index"))

    form = NewShopForm()
    if form.validate_on_submit():
        shop = Shop(shopname=form.shopname.data)
        db.session.add(shop)
        db.session.commit()
        flash("Stworzono nowy sklep")
        return redirect(url_for("index"))
    return render_template("new_shop.html", title="Grafiki - nowy sklep", form=form)


@app.route("/<path:path>")
def static_proxy(path):
    """
    Allows to send files between functions.
    """
    return app.send_static_file(path)


# Assigns user to the shop
@app.route("/workplace-worker-connect", methods=["GET", "POST"])
@login_required
def worker_to_workplace():
    """
    Allows to manage connections between workers and workplaces.
    """
    if current_user.access_level != "0" and current_user.access_level != "1":
        flash("Użytkownik nie ma uprawnień do wyświetlenia tej strony")
        return redirect(url_for("index"))

    form = UserToShopForm()
    workplaces = Shop.query.order_by(Shop.shopname).all()
    workplaces_list = []
    for workplace in workplaces:
        workplaces_list.append((str(workplace), str(workplace)))
    form.workplace.choices = workplaces_list

    workers = User.query.order_by(User.username).all()
    workers_list = []
    for worker in workers:
        workers_list.append((str(worker), str(worker)))
    form.worker.choices = workers_list

    users_number = len(workers_list)
    if form.validate_on_submit():
        worker = User.query.filter_by(username=form.worker.data).first()
        workplace = Shop.query.filter_by(shopname=form.workplace.data).first()
        already_assigned = workplace.works
        if worker not in already_assigned:
            workplace.works.append(worker)
            db.session.commit()
            flash("Przypisano %s do %s" % (worker, workplace))
        else:
            flash("%s był już przypisany do %s" % (worker, workplace))
        return redirect(url_for("worker_to_workplace"))
    return render_template("worker_to_workplace.html", title="Grafiki - przydzielanie użytkownika do sklepu",
                           form=form, workplaces=workplaces, users_number=users_number)


# jsonifies data for dynamically generated checkboxes in worker_to_workplace()
@app.route("/workplace-worker-connect/<workplace>")
@login_required
def worker_to_workplace_workers(workplace):
    """
    Makes list of workers unassigned to chosen workplace
    :param workplace: chosen workplace
    :return: list of workers
    """
    if current_user.access_level != "0" and current_user.access_level != "1":
        flash("Użytkownik nie ma uprawnień do wyświetlenia tej strony")
        return redirect(url_for("index"))
    shop = Shop.query.filter_by(shopname=workplace).first()
    workers_appended = shop.works.all()
    workers_all = User.query.order_by(User.username).all()
    workers = []
    for worker in workers_all:
        if worker not in workers_appended:
            workers.append(worker)
    jsondict = []
    for worker in workers:
        workers_list = {"name": worker.username}
        jsondict.append(workers_list)
    return jsonify({"workers": jsondict})


# removes connection between worker and workplace
@app.route("/remove-user-from-shop", methods=["GET", "POST"])
@login_required
def remove_from_shop():
    """
    Removes link between worker and workplace.
    """
    if (current_user.access_level != "0") and (current_user.access_level != "1"):
        flash("Użytkownik nie ma uprawnień do wyświetlenia tej strony")
        return redirect(url_for("index"))

    user = request.args.get("user")
    shop = request.args.get("shop")
    found_user = User.query.filter_by(username=user).first()
    found_workplace = Shop.query.filter_by(shopname=shop).first()
    found_workplace.works.remove(found_user)
    db.session.commit()
    flash("Usunięto %s z %s" % (user, shop))
    return redirect(url_for("worker_to_workplace"))


# gets beginning and duration of billing period
@app.route("/billing-period", methods=["GET", "POST"])
@login_required
def billing_period():
    """
    Allows to set beginning of counting billing periods and length of it in months.
    """
    if (current_user.access_level != "0") and (current_user.access_level != "1"):
        flash("Użytkownik nie ma uprawnień do wyświetlenia tej strony")
        return redirect(url_for("index"))
    form = BillingPeriod()
    if Billing_period.query.filter_by(id=1).first() is None:
        cur_begin = 1
    else:
        cur_begin = "{: %d - %m - %Y}".format(Billing_period.query.filter_by(id=1).first().begin)

    if Billing_period.query.filter_by(id=1).first() is None:
        cur_duration = 3
    else:
        cur_duration = Billing_period.query.filter_by(id=1).first().duration

    if form.validate_on_submit():
        begin = datetime(int(form.begin_year.data), int(form.begin_month.data), 1)
        duration = form.length_of_billing_period.data
        if not Billing_period.query.all() == 0:
            b_p = Billing_period(begin=begin, duration=duration)
            db.session.add(b_p)
            db.session.commit()
        else:
            b_p = Billing_period
            b_p.query.filter_by(id=1).all()[0].begin = begin
            b_p.query.filter_by(id=1).all()[0].duration = duration
            db.session.commit()
        flash("Zmieniono okres rozliczeniowy na: Początek: %s Długość: %s" % ("{:%d - %m - %Y}".format(begin),
                                                                              duration))
        return redirect(url_for("index"))
    return render_template("billing_period.html", title="Grafiki - okres rozliczeniowy", form=form,
                           cur_begin=cur_begin, cur_duration=cur_duration)


# gets data for new schedule and creates new schedule template
@app.route("/new-schedule", methods=["GET", "POST"])
@login_required
def new_schedule():
    """
    Creates template with empty, modifiable schedule for chosen year, month and workplace and with unmodifiable
    schedule for previous month.
    I'm not using calendar module's names for months and days because whole app has to be in polish,
    so the code is little more complicated.
    :return: template with all necessary data for new schedule
    """
    if current_user.access_level != "0" and current_user.access_level != "1" and current_user.access_level != "2":
        flash("Użytkownik nie ma uprawnień do wyświetlenia tej strony")
        return redirect(url_for("index"))

    workplaces = []
    workers_list = []
    form = NewScheduleForm()
    c_user = User.query.filter_by(username=str(current_user)).first()
    for workplace in c_user.workers_shop:
        workplaces.append((str(workplace), str(workplace)))
    form.workplace.choices = workplaces

    for worker in User.query.order_by(User.access_level).all():
        workers_list.append((str(worker), str(worker)))
    form.workers.choices = workers_list

    if form.validate_on_submit():
        workplace = form.workplace.data
        year = int(form.year.data)
        month = int(form.month.data)
        hours = form.hours.data
        month_names = ["Styczeń", "Luty", "Marzec", "Kwiecień", "Maj", "Czerwiec", "Lipiec", "Sierpień",
                       "Wrzesień", "Październik", "Listopad", "Grudzień"]
        month_name = month_names[month - 1]
        cal = calendar.Calendar()
        weekday_names = ["Poniedziałek", "Wtorek", "Środa", "Czwartek", "Piątek", "Sobota", "Niedziela"]

        schedule_name = "%s-%s-%s" % (year, month, workplace)
        check_schedule = Schedule.query.filter_by(name=schedule_name).first()
        if check_schedule is not None:
            flash("Taki grafik już istnieje")
            redirect(url_for("index"))
        else:
            workers_to_schd = []
            for worker in form.workers.data:
                workers_to_schd.append(str(worker).replace(" ", "_"))

            prev = prev_schedule(month, year, month_names, cal, workplace)
            print()
            try:
                return render_template("empty_schedule.html", title="Grafiki - nowy grafik", workers=workers_to_schd,
                                       shop=workplace, year=year, month=month, mn=month_name, cal=cal, wdn=weekday_names,
                                       hours=hours, Billing_period=Billing_period,
                                       prev_shdict=prev["prev_shdict"], prev_month=prev["month"],
                                       prev_month_name=prev["month_name"], prev_year=prev["year"],
                                       prev_hours=prev["hours"], prev_workers=prev["workers"],
                                       workers_hours=prev["workers_hours"])
            except:
                flash("Sprawdź, czy jest ustawiony początek okresu rozliczeniowego")
            redirect(url_for("new_schedule"))

    return render_template("new_schedule.html", title="Grafiki - nowy grafik", form=form)


# jsonifies data for dynamicly generated checkboxes in new_schedule()
@app.route("/new-schedule/<workplace>")
@login_required
def new_schedule_find_workers(workplace):
    """
    Finds workers assigned to chosen workplace and sends back list with them to template that allow to choose workers
    that will be in schedule.
    :param workplace: chosen workplace
    :return: jsonified list of workers assigned to chosen workplace
    """
    if current_user.access_level != "0" and current_user.access_level != "1" and current_user.access_level != "2":
        flash("Użytkownik nie ma uprawnień do wyświetlenia tej strony")
        return redirect(url_for("index"))

    shop = Shop.query.filter_by(shopname=workplace).first()
    workers = shop.works.all()
    jsondict = []
    for worker in shop.works.all():
        workers_list = {}
        if worker.access_level == "0" or worker.access_level == "1":
            workers.remove(worker)
        else:
            workers_list["name"] = worker.username
            jsondict.append(workers_list)
    return jsonify({"workers": jsondict})


# adds schedule to db
@app.route('/schedule-to-db/<action>', methods=['POST'])
@login_required
def new_schedule_to_db(action):
    """
    Adds new (unaccepted) schedule do database or replaces unaccepted version with accepted one
    :param action: tells function if it has to add new version to db or replace existing one with it's accepted version.
    """
    if current_user.access_level != "0" and current_user.access_level != "1" and current_user.access_level != "2":
        flash("Użytkownik nie ma uprawnień do wyświetlenia tej strony")
        return redirect(url_for("index"))

    def changes(old, new):
        changes_list = {}
        old_workers = []
        for old_p_schedule in old.ind:
            if old_p_schedule.worker not in old_workers:
                old_workers.append(str(old_p_schedule.worker))
        new_workers = []
        for new_p_schedule in new.ind:
            if new_p_schedule.worker not in new_workers:
                new_workers.append(str(new_p_schedule.worker))
        for worker in old_workers:
            if worker not in new_workers:
                changes_list[worker] = "Usunięto z grafiku"

        # Looking for changes in individual schedules
        for worker in new_workers:
            worker_changes = [worker]
            if worker not in old_workers:
                worker_changes.append("Dodano do grafiku")
            for pschedule in Personal_schedule.query.filter_by(worker=worker, includes_id=new.id):
                old_pschedule = Personal_schedule.query.filter_by(name=pschedule.name, includes_id=old.id).first()
                if old_pschedule is not None:
                    if pschedule.begin_hour != old_pschedule.begin_hour or pschedule.end_hour != old_pschedule.end_hour \
                            or pschedule.event != old_pschedule.event:
                        change_date = pschedule.date.strftime("%d.%m.%Y")
                        n_b_hour = pschedule.begin_hour
                        o_b_hour = old_pschedule.begin_hour
                        n_e_hour = pschedule.end_hour
                        o_e_hour = old_pschedule.end_hour
                        n_event = pschedule.event
                        if n_event == "off":
                            n_event = "wolne"
                        elif n_event == "in_work":
                            n_event = "w pracy"
                        o_event = old_pschedule.event
                        if o_event == "off":
                            o_event = "wolne"
                        elif o_event == "in_work":
                            o_event = "w pracy"
                        msg = "%s było %s-%s %s, a ma być %s-%s %s" % (change_date, o_b_hour, o_e_hour, o_event,
                                                                       n_b_hour, n_e_hour, n_event)
                        worker_changes.append(msg)
            changes_list[worker] = worker_changes
        for i in changes_list:
            for j in changes_list[i]:
                print(j)


    # adds individual schedules to db
    def ind_schedules_to_db(data, schedule, billing_period):
        """
        Adds individual schedule to database.
        :param data: json with all information for every individual schedule
        :param schedule:
        :param billing_period:
        """
        for element in data["ind_schedules"]:
            schd_date = date(int(element["year"]), int(element["month"]), int(element["day"]))
            worker = element["worker"].replace("_", " ")
            b_hour = element["from"]
            e_hour = element["to"]
            h_sum = element["sum"]
            event = element["event"]
            workplace = element["workplace"]
            psname = "%s-%s-%s" % (schd_date, worker, workplace)
            billing_week = element["billing_week"]
            pschedule = Personal_schedule(name=psname, date=schd_date, worker=worker, begin_hour=b_hour,
                                          end_hour=e_hour, hours_sum=h_sum, event=event, workplace=workplace,
                                          includes=schedule, billing_period=billing_period, billing_week=billing_week)
            db.session.add(pschedule)

    data = request.json
    unaccepted_schedule = Schedule.query.filter_by(
        name="%s-%s-%s" % (data["main_data"]["year"], data["main_data"]["month"],
                           data["main_data"]["workplace"]), accepted=False).first()


    # Creates new unaccepted schedule or unaccepted version of existing schedule
    if action in ("send_v_0", "modify_existing"):
        print(action)
        name = "%s-%s-%s" % (data["main_data"]["year"], data["main_data"]["month"], data["main_data"]["workplace"])
        year = int(data["main_data"]["year"])
        month = int(data["main_data"]["month"])
        workplace = data["main_data"]["workplace"]
        hours = data["main_data"]["hours"]
        billing_period = int(data["main_data"]["billing_period"])
        version = int(data["main_data"]["version"])
        schedule = Schedule(name=name, year=year, month=month, workplace=workplace, hrs_to_work=hours,
                            accepted=False, version=version, billing_period=billing_period)
        db.session.add(schedule)

        ind_schedules_to_db(data, schedule, billing_period)
        db.session.commit()

        old = Schedule.query.filter_by(name=name, version=version, accepted=True).first()
        new = schedule
        if old is not None:
            changes(old, new)


    # Accepts schedule and increase it's version number, deletes unaccepted version from db
    elif action == "accept_new_v":
        if current_user.access_level != "0" and current_user.access_level != "1":
            flash("Użytkownik nie ma uprawnień do wyświetlenia tej strony")
            return redirect(url_for("index"))

        name = unaccepted_schedule.name
        year = unaccepted_schedule.year
        month = unaccepted_schedule.month
        workplace = unaccepted_schedule.workplace
        hours = unaccepted_schedule.hrs_to_work
        accepted = True
        version = unaccepted_schedule.version + 1
        billing_period = unaccepted_schedule.billing_period
        schedule = Schedule(name=name, year=year, month=month, workplace=workplace, hrs_to_work=hours,
                            accepted=accepted, version=version, billing_period=billing_period)
        db.session.add(schedule)

        ind_schedules_to_db(data, schedule, billing_period)
        db.session.commit()

        old = unaccepted_schedule
        new = schedule
        if old is not None:
            changes(old, new)

        for ind_schedule in unaccepted_schedule.ind:
            db.session.delete(ind_schedule)
        db.session.delete(unaccepted_schedule)



    return url_for("index")
    # except AttributeError:
    # return "1"
    # except:
    # return "2"


# makes list of unaccepted schedule for current user
@app.route("/unaccepted_schedules", methods=["GET", "POST"])
@login_required
def unaccepted_schedules():
    """
    :return: shows list of every unaccepted schedules wchich current user can accept
    """
    if (current_user.access_level != "0") and (current_user.access_level != "1"):
        flash("Użytkownik nie ma uprawnień do wyświetlenia tej strony")
        return redirect(url_for("index"))

    los = list_of_schedules_acc_mod(mod_acc=False)

    return render_template("schedules-to-accept.html", title="Grafiki - niezaakceptowane grafiki", ua=los["schedules"],
                           sn=los["nos"], Schedule=Schedule)


# creates modifiable template with schedule
@app.route("/accept-schedule", methods=["GET", "POST"])
@login_required
def accept_modify_schedule():
    """
    :return: creates template with modifiable version of chosen unaccepted schedule and unmodifiable look
    at previous month schedule
    """
    action = request.args.get("action")
    schedule = None
    title = "Grafiki"
    print(action)

    if action == "to_accept":
        if (current_user.access_level != "0") and (current_user.access_level != "1"):
            flash("Użytkownik nie ma uprawnień do wyświetlenia tej strony")
            return redirect(url_for("index"))
        schedule = Schedule.query.filter_by(name=request.args.get("schd"), version=int(request.args.get("v")),
                                            accepted=False).first()
        title = "Grafiki - akceptacja grafiku"
    elif action == "to_modify":
        if (current_user.access_level != "0") and (current_user.access_level != "1") and\
                (current_user.access_level != "2"):
            flash("Użytkownik nie ma uprawnień do wyświetlenia tej strony")
            return redirect(url_for("index"))
        schedule = Schedule.query.filter_by(name=request.args.get("schd"), version=int(request.args.get("v")),
                                            accepted=True).first()
        title = "Grafiki - modyfikacja grafiku"
    if not schedule:
        flash("Nie ma takiego grafiku")
        return redirect(url_for("accept_modify_schedule"))
    schedule_id = schedule.id
    workplace = schedule.workplace
    year = schedule.year
    month = schedule.month
    hours = schedule.hrs_to_work
    version = schedule.version
    workers = []
    for pers_schedule in schedule.ind:
        if str(pers_schedule.worker).replace(" ", "_") not in workers:
            workers.append(str(pers_schedule.worker).replace(" ", "_"))

    month_names = ["Styczeń", "Luty", "Marzec", "Kwiecień", "Maj", "Czerwiec", "Lipiec", "Sierpień",
                   "Wrzesień", "Październik", "Listopad", "Grudzień"]
    weekday_names = ["Poniedziałek", "Wtorek", "Środa", "Czwartek", "Piątek", "Sobota", "Niedziela"]
    month_name = month_names[month - 1]
    cal = calendar.Calendar()

    prev = prev_schedule(month, year, month_names, cal, workplace)

    shdict = {}
    for worker in workers:
        for day in cal.itermonthdays(year, month):
            if day > 0:
                begin = Personal_schedule.query.filter_by(date=datetime(year, month, day), includes_id=schedule_id,
                                                          worker=worker.replace("_", " ")).first().begin_hour
                end = Personal_schedule.query.filter_by(date=datetime(year, month, day), includes_id=schedule_id,
                                                        worker=worker.replace("_", " ")).first().end_hour
                event = Personal_schedule.query.filter_by(date=datetime(year, month, day), includes_id=schedule_id,
                                                          worker=worker.replace("_", " ")).first().event
                if begin == 0:
                    begin = ""
                shdict["begin-%s-%d-%02d-%02d" % (worker, year, month, day)] = begin
                if end == 0:
                    end = ""
                shdict["end-%s-%d-%02d-%02d" % (worker, year, month, day)] = end
                shdict["event-%s-%d-%02d-%02d" % (worker, year, month, day)] = event

    return render_template("accept-schedule.html", action=action, title=title, schedule=schedule, workplace=workplace,
                           year=year, month=month, workers=workers, month_name=month_name, wdn=weekday_names, cal=cal,
                           Billing_period=Billing_period, version=version, shdict=shdict, hours=hours,
                           prev_shdict=prev["prev_shdict"], prev_month=prev["month"], prev_hours=prev["hours"],
                           prev_month_name=prev["month_name"], prev_year=prev["year"], prev_workers=prev["workers"],
                           workers_hours=prev["workers_hours"])


# makes list of schedules modifiable by current user
@app.route("/modifiable-schedules", methods=["GET", "POST"])
@login_required
def modifiable_schedules():
    """
    :return: renders template with form that allows to filter all accepted schedules and chose one to modify
    """
    if (current_user.access_level != "0") and (current_user.access_level != "1") and (current_user.access_level != "2"):
        flash("Użytkownik nie ma uprawnień do wyświetlenia tej strony")
        return redirect(url_for("index"))

    month_names = ["Styczeń", "Luty", "Marzec", "Kwiecień", "Maj", "Czerwiec", "Lipiec", "Sierpień",
                   "Wrzesień", "Październik", "Listopad", "Grudzień"]

    return render_template("schedules-to-modify.html", title="Grafiki - modyfikowalne grafiki", mn=month_names)


# jsonifies data for dynamicly generated filtered list of schedules in modifiable_schedules()
@app.route("/filter_schedules/<year>/<month>/<workplace>")
@login_required
def filter_schedules_to_modify(year, month, workplace):
    """
    Finds schedule that matches filter criteria.
    :param year: year of schedule
    :param month: month of schedule
    :param workplace: workplace of schedule
    :return: matching schedule
    """
    if current_user.access_level != "0" and current_user.access_level != "1" and current_user.access_level != "2":
        flash("Użytkownik nie ma uprawnień do wyświetlenia tej strony")
        return redirect(url_for("index"))

    schedules = Schedule.query.filter_by(year=int(year), month=int(month), workplace=workplace, accepted=True).all()


    # finds latest version of
    def find_latest_version_schd(schedules, workplace):
        """
        Only latest version can be modified.
        :param schedules: all schedules for chosen workplace
        :param workplace: chosen workplace
        """
        versions = []
        for schedule in schedules:
            versions.append(schedule.version)

        highest_version = max(versions)
        filtered = Schedule.query.filter_by(year=int(year), month=int(month), workplace=workplace,
                                            version=highest_version, accepted=True).first()
        return filtered


    if workplace != "0":
        print("dla jednego sklepu")
        print(schedules)
        if not schedules:
            return jsonify({"option": 0})
        uri = url_for("accept_modify_schedule", schd=filtered.name, v=filtered.version, action="to_modify")
        filtered = find_latest_version_schd(schedules, workplace)
        return jsonify({"option": 1, "schedules": [{"url": uri, "name": filtered.name, "year": filtered.year,
                                                   "month": filtered.month, "workplace": filtered.workplace,
                                                   "version": filtered.version}]})

    workplaces = current_user.workers_shop
    json_schedules = []
    for users_workplace in workplaces:
        schedules = Schedule.query.filter_by(year=int(year), month=int(month), workplace=users_workplace.shopname,
                                             accepted=True).all()
        if schedules:
            filtered = find_latest_version_schd(schedules, users_workplace.shopname)
            if filtered is not None:
                uri = url_for("accept_modify_schedule", schd=filtered.name, v=filtered.version, action="to_modify")
                json_schedules.append({"url": uri, "name": filtered.name, "year": filtered.year, "month": filtered.month,
                                       "workplace": filtered.workplace, "version": filtered.version})
    if not json_schedules:
        return jsonify({"option": 0})
    return jsonify({"option": 1, "schedules": json_schedules})
