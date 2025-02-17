# app.py - 肺结节患者随访系统

from flask import Flask, render_template, redirect, url_for, send_file
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import FlaskForm
from wtforms import StringField, DateField, FloatField, TextAreaField, SubmitField, IntegerField
from wtforms.validators import DataRequired, Optional
import datetime
import csv
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///patients.db'
db = SQLAlchemy(app)

# 数据库模型
class Patient(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=False)
    gender = db.Column(db.String(10))
    age = db.Column(db.Integer)
    contact = db.Column(db.String(20))  # 新增联系方式字段
    initial_diagnosis_date = db.Column(db.Date)
    nodule_size = db.Column(db.Float)
    nodule_location = db.Column(db.String(120))
    followups = db.relationship('Followup', backref='patient', lazy=True)

class Followup(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    followup_date = db.Column(db.Date, default=datetime.date.today)
    checkup_type = db.Column(db.String(80))  # CT/MRI/X-ray等
    nodule_size = db.Column(db.Float)
    findings = db.Column(db.Text)
    patient_id = db.Column(db.Integer, db.ForeignKey('patient.id'))

# 表单定义
class PatientForm(FlaskForm):
    name = StringField('患者姓名', validators=[DataRequired()])
    gender = StringField('性别', validators=[Optional()])
    age = IntegerField('年龄', validators=[Optional()])
    contact = StringField('联系方式(手机号)', validators=[Optional()])  # 新增联系方式字段
    initial_diagnosis_date = DateField('初诊日期', format='%Y-%m-%d', validators=[Optional()])
    nodule_size = FloatField('结节大小(mm)', validators=[Optional()])
    nodule_location = StringField('结节位置', validators=[Optional()])
    submit = SubmitField('保存')

class FollowupForm(FlaskForm):
    followup_date = DateField('随访日期', default=datetime.date.today, format='%Y-%m-%d', validators=[Optional()])
    checkup_type = StringField('检查类型', validators=[Optional()])
    nodule_size = FloatField('当前结节大小(mm)', validators=[Optional()])
    findings = TextAreaField('检查发现', validators=[Optional()])
    submit = SubmitField('添加随访记录')

# CSV写入辅助函数
def append_patient_to_csv(patient):
    file_exists = os.path.isfile('patients.csv')
    with open('patients.csv', 'a', newline='', encoding='utf-8') as csvfile:
        fieldnames = ['id', 'name', 'gender', 'age', 'contact', 'initial_diagnosis_date', 'nodule_size', 'nodule_location']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        if not file_exists:
            writer.writeheader()
        writer.writerow({
            'id': patient.id,
            'name': patient.name,
            'gender': patient.gender,
            'age': patient.age,
            'contact': patient.contact,
            'initial_diagnosis_date': patient.initial_diagnosis_date.strftime('%Y-%m-%d') if patient.initial_diagnosis_date else '',
            'nodule_size': patient.nodule_size,
            'nodule_location': patient.nodule_location,
        })

def append_followup_to_csv(followup):
    file_exists = os.path.isfile('followups.csv')
    with open('followups.csv', 'a', newline='', encoding='utf-8') as csvfile:
        fieldnames = ['id', 'patient_id', 'followup_date', 'checkup_type', 'nodule_size', 'findings']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        if not file_exists:
            writer.writeheader()
        writer.writerow({
            'id': followup.id,
            'patient_id': followup.patient_id,
            'followup_date': followup.followup_date.strftime('%Y-%m-%d') if followup.followup_date else '',
            'checkup_type': followup.checkup_type,
            'nodule_size': followup.nodule_size,
            'findings': followup.findings,
        })

# 路由定义
@app.route('/')
def index():
    patients = Patient.query.order_by(Patient.initial_diagnosis_date.desc()).all()
    return render_template('patient_list.html', patients=patients)

@app.route('/patient/<int:id>')
def patient_detail(id):
    patient = Patient.query.get_or_404(id)
    return render_template('patient_detail.html', patient=patient)

@app.route('/add_patient', methods=['GET', 'POST'])
def add_patient():
    form = PatientForm()
    if form.validate_on_submit():
        patient = Patient(
            name=form.name.data,
            gender=form.gender.data,
            age=form.age.data,
            contact=form.contact.data,
            initial_diagnosis_date=form.initial_diagnosis_date.data,
            nodule_size=form.nodule_size.data,
            nodule_location=form.nodule_location.data
        )
        db.session.add(patient)
        db.session.commit()
        # 将新增患者写入CSV文件
        append_patient_to_csv(patient)
        return redirect(url_for('index'))
    return render_template('add_patient.html', form=form)

@app.route('/add_followup/<int:patient_id>', methods=['GET', 'POST'])
def add_followup(patient_id):
    form = FollowupForm()
    if form.validate_on_submit():
        followup = Followup(
            followup_date=form.followup_date.data,
            checkup_type=form.checkup_type.data,
            nodule_size=form.nodule_size.data,
            findings=form.findings.data,
            patient_id=patient_id
        )
        db.session.add(followup)
        db.session.commit()
        # 将新增随访记录写入CSV文件
        append_followup_to_csv(followup)
        return redirect(url_for('patient_detail', id=patient_id))
    return render_template('add_followup.html', form=form, patient_id=patient_id)

# CSV文件下载路由
@app.route('/download_patients')
def download_patients():
    if not os.path.isfile('patients.csv'):
        return "没有患者数据CSV文件。", 404
    return send_file('patients.csv', as_attachment=True, download_name='patients.csv', mimetype='text/csv')

@app.route('/download_followups')
def download_followups():
    if not os.path.isfile('followups.csv'):
        return "没有随访数据CSV文件。", 404
    return send_file('followups.csv', as_attachment=True, download_name='followups.csv', mimetype='text/csv')

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True, port=5000)
