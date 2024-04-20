from flask import render_template, request, redirect, url_for, Blueprint
import psycopg2

links_bp = Blueprint('links', __name__)


def db_conn():
    conn = psycopg2.connect(database="mrp", host="localhost", user="postgres", password="asdf56y", port="5432")
    return conn


@links_bp.route('/links')
def links_index():
    conn = db_conn()
    cur = conn.cursor()
    cur.execute('''SELECT l.id, 
                          l.upperNodeName, 
                          n1.nodeName AS upperNodeFullName, 
                          l.lowerNodeName, 
                          n2.nodeName AS lowerNodeFullName, 
                          l.weight, 
                          l.unitOfMeasurement 
                   FROM links l
                   INNER JOIN nodes n1 ON l.upperNodeName = n1.id
                   INNER JOIN nodes n2 ON l.lowerNodeName = n2.id
                   ORDER by l.id''')
    data = cur.fetchall()
    cur.close()
    conn.close()
    return render_template('links.html', data=data)


@links_bp.route('/links/create', methods=['POST'])
def links_create():
    conn = db_conn()
    cur = conn.cursor()
    upper_node_id = request.form['upper_node_id']
    lower_node_id = request.form['lower_node_id']
    weight = request.form['weight']
    unit_of_measurement = request.form['unit_of_measurement']
    cur.execute(
        '''INSERT INTO links (upperNodeName, lowerNodeName, weight, unitOfMeasurement) 
           VALUES(%s, %s, %s, %s)''',
        (upper_node_id, lower_node_id, weight, unit_of_measurement)
    )
    conn.commit()
    cur.close()
    conn.close()
    return redirect(url_for('links.links_index'))


@links_bp.route('/links/update', methods=['POST'])
def links_update():
    conn = db_conn()
    cur = conn.cursor()

    # Получаем значения из формы
    upper_node_full_name = request.form['upper_node_full_name']
    lower_node_full_name = request.form['lower_node_full_name']
    weight = request.form['weight']
    unit_of_measurement = request.form['unit_of_measurement']
    link_id = request.form['id']

    # Получаем идентификаторы узлов на основе их полных имен
    cur.execute('''SELECT id FROM nodes WHERE nodeName = %s''', (upper_node_full_name,))
    result = cur.fetchone()
    if result:
        upper_node_id = result[0]
    else:
        # Обработка случая, когда узел верхнего уровня не найден
        # Можно вернуть сообщение об ошибке или выполнить другие действия по вашему усмотрению
        # В данном случае я просто возвращаю пустой ответ
        return "Ошибка: Узел верхнего уровня не найден"

    cur.execute('''SELECT id FROM nodes WHERE nodeName = %s''', (lower_node_full_name,))
    result = cur.fetchone()
    if result:
        lower_node_id = result[0]
    else:
        # Обработка случая, когда узел нижнего уровня не найден
        # Можно вернуть сообщение об ошибке или выполнить другие действия по вашему усмотрению
        # В данном случае я просто возвращаю пустой ответ
        return "Ошибка: Узел нижнего уровня не найден"

    # Обновляем запись в базе данных с использованием идентификаторов узлов
    cur.execute(
        '''UPDATE links 
           SET upperNodeName = %s, lowerNodeName = %s, weight = %s, unitOfMeasurement = %s 
           WHERE id = %s''',
        (upper_node_id, lower_node_id, weight, unit_of_measurement, link_id)
    )
    conn.commit()
    cur.close()
    conn.close()

    return redirect(url_for('links.links_index'))


@links_bp.route('/links/delete', methods=['POST'])
def links_delete():
    conn = db_conn()
    cur = conn.cursor()
    link_id = request.form['id']
    cur.execute('''DELETE FROM links WHERE id=%s''', (link_id,))
    conn.commit()
    cur.close()
    conn.close()
    return redirect(url_for('links.links_index'))


# ---- Links CRUD Operations ----
@links_bp.route('/links/get', methods=['GET'])
def links_get():
    id = request.args.get('id', '')

    conn = db_conn()
    cur = conn.cursor()

    if id:
        cur.execute('''SELECT l.id, 
                              l.upperNodeName, 
                              n1.nodeName AS upperNodeFullName, 
                              l.lowerNodeName, 
                              n2.nodeName AS lowerNodeFullName, 
                              l.weight, 
                              l.unitOfMeasurement 
                       FROM links l
                       INNER JOIN nodes n1 ON l.upperNodeName = n1.id
                       INNER JOIN nodes n2 ON l.lowerNodeName = n2.id
                       WHERE l.id = %s''', (id,))
    else:
        cur.execute('''SELECT l.id, 
                              l.upperNodeName, 
                              n1.nodeName AS upperNodeFullName, 
                              l.lowerNodeName, 
                              n2.nodeName AS lowerNodeFullName, 
                              l.weight, 
                              l.unitOfMeasurement 
                       FROM links l
                       INNER JOIN nodes n1 ON l.upperNodeName = n1.id
                       INNER JOIN nodes n2 ON l.lowerNodeName = n2.id''')

    data = cur.fetchall()
    cur.close()
    conn.close()

    if not data:
        return render_template('links.html', error='No links found')

    return render_template('links.html', data=data)