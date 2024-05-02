from flask import Flask, render_template, request, redirect, url_for
from links import links_bp
from orders import orders_bp
from nodes import nodes_bp
from nodes_details import nodes_details_bp
from warehouse import warehouse_bp
from difference import difference_bp
import psycopg2


app = Flask(__name__)
app.register_blueprint(links_bp)
app.register_blueprint(orders_bp)
app.register_blueprint(nodes_bp)
app.register_blueprint(nodes_details_bp)
app.register_blueprint(warehouse_bp)
app.register_blueprint(difference_bp)

def db_conn():
    conn = psycopg2.connect(database="mrp", host="localhost", user="postgres", password="asdf56y", port="5432")
    return conn


@app.route('/')
def home():
    return render_template('layout.html')


if __name__ == '__main__':
    app.run(debug=True)
