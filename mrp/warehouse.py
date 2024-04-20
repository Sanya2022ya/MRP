from flask import render_template, request, redirect, url_for, Blueprint
import psycopg2

warehouse_bp = Blueprint('warehouse', __name__)


def db_conn():
    conn = psycopg2.connect(database="mrp", host="localhost", user="postgres", password="asdf56y", port="5432")
    return conn


@warehouse_bp.route('/warehouse')
def warehouse_index():
    conn = db_conn()
    cur = conn.cursor()

    # Выполняем JOIN запрос для получения данных из таблицы warehouse и nodes
    cur.execute('''
        SELECT w.id, w.nodeId, n.nodeName, w.receivedQuantity, w.shippedQuantity, w.date
        FROM warehouse w
        JOIN nodes n ON w.nodeId = n.id
        ORDER BY w.id
    ''')

    data = cur.fetchall()
    cur.close()
    conn.close()

    # Передаем данные в шаблон
    return render_template('warehouse.html', data=data)


@warehouse_bp.route('/warehouse/create', methods=['GET', 'POST'])
def warehouse_create():
    conn = db_conn()
    cur = conn.cursor()

    # Если метод POST, обработайте отправку формы
    if request.method == 'POST':
        node_id = request.form['node_id']
        received_quantity = request.form['received_quantity']
        shipped_quantity = request.form['shipped_quantity']
        date = request.form['date']

        # Выполните вставку нового склада в таблицу
        cur.execute('''INSERT INTO warehouse (nodeId, receivedQuantity, shippedQuantity, date)
                        VALUES (%s, %s, %s, %s)''',
                    (node_id, received_quantity, shipped_quantity, date))

        conn.commit()
        cur.close()
        conn.close()
        return redirect(url_for('warehouse.warehouse_index'))

    # Если метод GET, получите список узлов и передайте его в шаблон
    cur.execute('''SELECT id, nodeName FROM nodes''')
    nodes = cur.fetchall()
    cur.close()
    conn.close()

    return render_template('warehouse_create.html', nodes=nodes)


@warehouse_bp.route('/warehouse/update', methods=['POST'])
def warehouse_update():
    conn = db_conn()
    cur = conn.cursor()

    # Получаем данные из формы
    node_id = request.form['node_id']
    received_quantity = request.form['received_quantity']
    shipped_quantity = request.form['shipped_quantity']
    date = request.form['date']
    warehouse_id = request.form['id']

    # Извлекаем node_name на основе node_id
    cur.execute('SELECT nodeName FROM nodes WHERE id = %s', (node_id,))
    node_name_result = cur.fetchone()
    if node_name_result:
        node_name = node_name_result[0]  # Получаем значение node_name

        # Обновляем запись в таблице warehouse
        cur.execute('''
            UPDATE warehouse
            SET nodeId = %s, receivedQuantity = %s, shippedQuantity = %s, date = %s
            WHERE id = %s
        ''', (node_id, received_quantity, shipped_quantity, date, warehouse_id))

        # Сохраняем изменения
        conn.commit()

    # Закрываем соединение и курсор
    cur.close()
    conn.close()

    # Перенаправляем на страницу warehouse_index
    return redirect(url_for('warehouse.warehouse_index'))


@warehouse_bp.route('/warehouse/delete', methods=['POST'])
def warehouse_delete():
    conn = db_conn()
    cur = conn.cursor()
    warehouse_id = request.form['id']
    cur.execute('''DELETE FROM warehouse WHERE id=%s''', (warehouse_id,))
    conn.commit()
    cur.close()
    conn.close()
    return redirect(url_for('warehouse.warehouse_index'))


@warehouse_bp.route('/warehouse/get', methods=['GET'])
def warehouse_get():
    search = request.args.get('search', '')

    conn = db_conn()
    cur = conn.cursor()

    if search:
        cur.execute('''SELECT * FROM warehouse WHERE nodeId = %s''', (search,))
    else:
        cur.execute('''SELECT * FROM warehouse''')

    data = cur.fetchall()
    cur.close()
    conn.close()

    if not data:
        return render_template('warehouse.html', error='No warehouse found')

    return render_template('warehouse.html', data=data)


@warehouse_bp.route('/warehouse/stock', methods=['GET'])
def get_stock():
    date = request.args.get('date')  # Получаем дату из запроса

    conn = db_conn()
    cur = conn.cursor()

    # Выполняем JOIN-запрос, чтобы получить nodeName вместо nodeId, но сортируем по nodeId
    cur.execute('''SELECT nodes.nodeName, SUM(warehouse.receivedQuantity - warehouse.shippedQuantity) AS stock 
                   FROM warehouse 
                   JOIN nodes ON warehouse.nodeId = nodes.id 
                   WHERE warehouse.date <= %s 
                   GROUP BY nodes.nodeName, nodes.id
                   ORDER BY nodes.id''', (date,))
    data = cur.fetchall()

    cur.close()
    conn.close()

    if not data:
        return 'Данные не найдены'

    # Формируем строку для отображения результатов
    result = []
    for row in data:
        result.append(f'Имя узла: {row[0]}, Количество товара на складе: {row[1]}')

    # Возвращаем результат, разделенный переносами строки
    return '\n'.join(result)



