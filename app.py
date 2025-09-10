import os
from datetime import datetime
from flask import Flask, render_template, request, redirect, flash, Response
from flask_sqlalchemy import SQLAlchemy
import csv
import io
import re

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "change_this_in_prod")

# Database configuration:
basedir = os.path.abspath(os.path.dirname(__file__))

# If Render or any host provides DATABASE_URL, use it; otherwise use local sqlite file.
DATABASE_URL = os.environ.get("DATABASE_URL")
if DATABASE_URL:
    SQLALCHEMY_DATABASE_URI = DATABASE_URL
else:
    SQLALCHEMY_DATABASE_URI = f"sqlite:///{os.path.join(basedir, 'data.db')}"

app.config["SQLALCHEMY_DATABASE_URI"] = SQLALCHEMY_DATABASE_URI
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)

class Customer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    branch_name = db.Column(db.String(200))
    branch_code = db.Column(db.String(100))
    customer_name = db.Column(db.String(200))
    customer_address = db.Column(db.String(500))
    customer_mobile = db.Column(db.String(20))
    remarks = db.Column(db.String(500))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

def validate_mobile(mobile):
    if not mobile:
        return None
    digits = re.sub(r'\D', '', mobile)
    return digits if len(digits) == 10 else None

@app.route('/', methods=['GET'])
def index():
    return render_template('form.html')

@app.route('/submit', methods=['POST'])
def submit():
    branch_name = request.form.get('branch_name', '').strip()
    branch_code = request.form.get('branch_code', '').strip()
    customer_name = request.form.get('customer_name', '').strip()
    customer_address = request.form.get('customer_address', '').strip()
    customer_mobile_raw = request.form.get('customer_mobile', '').strip()
    remarks = request.form.get('remarks', '').strip()

    mobile = validate_mobile(customer_mobile_raw)
    if not mobile:
        flash("Invalid mobile number. Enter 10 digits.")
        return redirect('/')

    cust = Customer(
        branch_name=branch_name,
        branch_code=branch_code,
        customer_name=customer_name,
        customer_address=customer_address,
        customer_mobile=mobile,
        remarks=remarks
    )
    db.session.add(cust)
    db.session.commit()
    flash("Record saved successfully.")
    return redirect('/view')

@app.route('/view')
def view():
    q = request.args.get('q', '').strip()
    if q:
        like = f"%{q}%"
        data = Customer.query.filter(
            (Customer.branch_name.ilike(like)) |
            (Customer.branch_code.ilike(like)) |
            (Customer.customer_name.ilike(like)) |
            (Customer.customer_mobile.ilike(like))
        ).order_by(Customer.created_at.desc()).all()
    else:
        data = Customer.query.order_by(Customer.created_at.desc()).all()
    return render_template('view.html', data=data, query=q)

@app.route('/export')
def export_csv():
    rows = Customer.query.order_by(Customer.id).all()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['ID','Branch Name','Branch Code','Customer Name','Address','Mobile','Remarks','Created At'])
    for r in rows:
        writer.writerow([r.id, r.branch_name, r.branch_code, r.customer_name, r.customer_address, r.customer_mobile, r.remarks, r.created_at])
    output.seek(0)
    return Response(output.getvalue(), mimetype="text/csv",
                    headers={"Content-Disposition":"attachment;filename=customers_export.csv"})

if __name__ == '__main__':
    # create tables if not exist (safe for first run)
    db.create_all()
    port = int(os.environ.get('PORT', 5000))
    # Local dev: listens on 0.0.0.0 so mobile can access via LAN; on Render gunicorn will be used.
    app.run(host='0.0.0.0', port=port, debug=True)
