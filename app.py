from flask import Flask, render_template, request, redirect, url_for, flash, session
from db import query_db, execute_db
from auth import auth_bp
import re, html

app = Flask(__name__)
app.secret_key = "e356a316f91c397ea812a552a3e7cc10e1ba81b9b8ed1fa1"

app.register_blueprint(auth_bp)

def user_has_role(username, role_desc):
    roles = query_db("""
        SELECT r.rDescription 
        FROM Act a
        JOIN Role r ON a.roleID = r.roleID
        WHERE a.userName = %s
    """, (username,))
    return any(r['rDescription'] == role_desc for r in roles)

@app.route('/')
def index():
    return render_template('dashboard.html')

@app.route('/dashboard')
def dashboard():
    if 'username' not in session:
        return redirect(url_for('auth.login'))
    return render_template('dashboard.html', username=session['username'])

@app.route('/edit_profile', methods=['GET', 'POST'])
def edit_profile():
    if 'username' not in session:
        flash("Please log in.", "error")
        return redirect(url_for('auth.login'))

    username = session['username']
    if request.method == 'POST':
        new_email = request.form.get('email','').strip()
        phone = request.form.get('phone','').strip()

        if not re.match(r'^[^@]+@[^@]+\.[^@]+$', new_email):
            flash("Invalid email address.", "error")
            return render_template('edit_profile.html')

        try:
            execute_db("UPDATE Person SET email=%s WHERE userName=%s", (new_email, username))
            if phone:
                existing = query_db("SELECT * FROM PersonPhone WHERE userName=%s", (username,))
                if existing:
                    execute_db("UPDATE PersonPhone SET phone=%s WHERE userName=%s", (phone, username))
                else:
                    execute_db("INSERT INTO PersonPhone(userName, phone) VALUES(%s,%s)", (username, phone))
            flash("Profile updated!", "success")
            return redirect(url_for('dashboard'))
        except Exception as e:
            flash("DB Error: " + str(e), "error")
            return render_template('edit_profile.html')

    user = query_db("SELECT fname, lname, email FROM Person WHERE userName=%s", (username,))
    phones = query_db("SELECT phone FROM PersonPhone WHERE userName=%s", (username,))
    return render_template('edit_profile.html', user=user[0] if user else {}, phone=phones[0]['phone'] if phones else '')

@app.route('/add_donation', methods=['GET','POST'])
def add_donation():
    if 'username' not in session:
        flash("Please log in first.", "error")
        return redirect(url_for('auth.login'))

    if request.method == 'POST':
        item_id = request.form.get('itemID','').strip()
        notes = request.form.get('notes','').strip()
        notes = html.escape(notes)  # The schema doesn't have notes column in DonatedBy, so this is just a placeholder

        if not item_id.isdigit():
            flash("Invalid Item ID.", "error")
            return render_template('add_donation.html')

        item_exists = query_db("SELECT ItemID FROM Item WHERE ItemID=%s",(item_id,))
        if not item_exists:
            flash("Item does not exist.", "error")
            return render_template('add_donation.html')

        try:
            # donateDate is DATE; use CURDATE()
            execute_db("INSERT INTO DonatedBy(ItemID,userName,donateDate) VALUES(%s,%s,CURDATE())",
                       (item_id, session['username']))
            flash("Donation recorded!", "success")
            return redirect(url_for('dashboard'))
        except Exception as e:
            flash("Error: " + str(e), "error")

    return render_template('add_donation.html')

@app.route('/donor_history')
def donor_history():
    if 'username' not in session:
        return redirect(url_for('auth.login'))

    username = session['username']
    summary = query_db("""
        SELECT COUNT(*) AS total_items, 
               MIN(donateDate) AS first_donation, MAX(donateDate) AS last_donation
        FROM DonatedBy
        WHERE userName=%s
    """, (username,))

    detail = query_db("""
        SELECT d.ItemID, i.iDescription, d.donateDate
        FROM DonatedBy d
        JOIN Item i ON d.ItemID=i.ItemID
        WHERE d.userName=%s
        ORDER BY d.donateDate DESC
    """, (username,))

    return render_template('donor_history.html', summary=summary[0] if summary else {}, donations=detail)

@app.route('/bulk_update_location', methods=['GET','POST'])
def bulk_update_location():
    if 'username' not in session:
        return redirect(url_for('auth.login'))

    if not user_has_role(session['username'], 'staff'):
        flash("You must be staff to do this.", "error")
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        itemIDs = request.form.get('itemIDs','').split(',')
        itemIDs = [i.strip() for i in itemIDs if i.strip().isdigit()]
        roomNum = request.form.get('roomNum','').strip()
        shelfNum = request.form.get('shelfNum','').strip()

        if not itemIDs or not roomNum.isdigit() or not shelfNum.isdigit():
            flash("Please provide valid item IDs and numeric location.", "error")
            return render_template('bulk_update_location.html')

        # Update location in Piece table
        placeholders = ','.join(['%s']*len(itemIDs))
        query = f"UPDATE Piece SET roomNum=%s, shelfNum=%s WHERE ItemID IN ({placeholders})"
        args = [roomNum, shelfNum] + itemIDs
        try:
            execute_db(query, args)
            flash("Locations updated!", "success")
            return redirect(url_for('dashboard'))
        except Exception as e:
            flash("Error: " + str(e), "error")

    return render_template('bulk_update_location.html')

@app.route('/order_progress')
def order_progress():
    progress = query_db("""
        SELECT o.orderID, o.orderNotes,
               COUNT(CASE WHEN i.found = TRUE THEN 1 END) AS items_found,
               COUNT(CASE WHEN i.found = FALSE THEN 1 END) AS items_missing
        FROM Ordered o
        JOIN ItemIn i ON o.orderID = i.orderID
        GROUP BY o.orderID, o.orderNotes
    """)
    return render_template('order_progress.html', orders=progress)

@app.route('/rank_volunteers')
def rank_volunteers():
    start_date = request.args.get('start','2024-01-01')
    end_date = request.args.get('end','2024-12-31')
    ranking = query_db("""
        SELECT d.userName, COUNT(*) AS deliveries_count
        FROM Delivered d
        JOIN Person p ON d.userName=p.userName
        WHERE d.date BETWEEN %s AND %s
        GROUP BY d.userName
        ORDER BY deliveries_count DESC
    """,(start_date,end_date))
    return render_template('rank_volunteers.html', ranking=ranking, start=start_date, end=end_date)

@app.errorhandler(404)
def page_not_found(e):
    return render_template('base.html', error="Page not found"), 404

@app.errorhandler(500)
def internal_error(e):
    return render_template('base.html', error="An internal error occurred."), 500

if __name__ == '__main__':
    app.run(debug=True)

