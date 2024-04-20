from flask import render_template, request, redirect, url_for, Blueprint
import psycopg2

nodes_bp = Blueprint('nodes', __name__)


def db_conn():
    conn = psycopg2.connect(database="mrp", host="localhost", user="postgres", password="asdf56y", port="5432")
    return conn


# ---- Nodes CRUD Operations ----
@nodes_bp.route('/nodes')
def nodes_index():
    conn = db_conn()
    cur = conn.cursor()
    cur.execute('''SELECT * FROM nodes ORDER by id''')
    data = cur.fetchall()
    cur.close()
    conn.close()
    return render_template('nodes.html', data=data)


@nodes_bp.route('/nodes/create', methods=['POST'])
def nodes_create():
    conn = db_conn()
    cur = conn.cursor()
    nodename = request.form['nodename']
    nodedescription = request.form['nodedescription']
    cur.execute('''INSERT INTO nodes (nodename, nodedescription) VALUES(%s, %s)''', (nodename, nodedescription))
    conn.commit()
    cur.close()
    conn.close()
    return redirect(url_for('nodes.nodes_index'))


@nodes_bp.route('/nodes/update', methods=['POST'])
def nodes_update():
    conn = db_conn()
    cur = conn.cursor()
    nodename = request.form['nodename']
    nodedescription = request.form['nodedescription']
    node_id = request.form['id']
    cur.execute('''UPDATE nodes SET nodename=%s, nodedescription=%s WHERE id=%s''',
                (nodename, nodedescription, node_id))
    conn.commit()
    return redirect(url_for('nodes.nodes_index'))


@nodes_bp.route('/nodes/delete', methods=['POST'])
def nodes_delete():
    conn = db_conn()
    cur = conn.cursor()
    node_id = request.form['id']
    cur.execute('''DELETE FROM nodes WHERE id=%s''', (node_id,))
    conn.commit()
    cur.close()
    conn.close()
    return redirect(url_for('nodes.nodes_index'))


@nodes_bp.route('/nodes/get', methods=['GET'])
def nodes_get():
    node_name = request.args.get('search', '')

    conn = db_conn()
    cur = conn.cursor()
    cur.execute('''SELECT * FROM nodes WHERE nodename ILIKE %s''', ('%' + node_name + '%',))
    data = cur.fetchall()
    cur.close()
    conn.close()

    if not data:
        return render_template('nodes.html', data=data, error='Node with the specified name not found')

    return render_template('nodes.html', data=data)