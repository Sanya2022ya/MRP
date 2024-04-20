from flask import render_template, request, redirect, url_for, Blueprint
import psycopg2

nodes_details_bp = Blueprint('nodes_details', __name__)


def db_conn():
    # Создаем подключение к базе данных
    conn = psycopg2.connect(database="mrp", host="localhost", user="postgres", password="asdf56y", port="5432")
    return conn


@nodes_details_bp.route('/nodes/details')
def nodes_details():
    # Получаем node_id из запроса
    node_id = request.args.get('node_id')

    if node_id:
        # Если передан node_id, выполняем запрос к базе данных
        conn = db_conn()
        cur = conn.cursor()

        try:
            # Преобразуем node_id в целое число
            node_id_int = int(node_id)
            # Запрос на получение информации о верхнем узле
            cur.execute('''SELECT * FROM nodes WHERE id = %s''', (node_id_int,))
            upper_node = cur.fetchone()

            # Получаем промежуточные и крайне низкие узлы для данного узла
            intermediate_nodes, lowest_nodes = get_intermediate_and_lowest_nodes(cur, node_id_int)

            # Вычисляем веса для промежуточных и крайне низких узлов
            for i, node in enumerate(intermediate_nodes):
                weight = compute_weight_for_node(cur, upper_node[0], node[0])
                # Добавляем вес к информации об узлах
                intermediate_nodes[i] = node + (weight,)

            for i, node in enumerate(lowest_nodes):
                weight = compute_weight_for_node(cur, upper_node[0], node[0])
                # Добавляем вес к информации об узлах
                lowest_nodes[i] = node + (weight,)

            # Закрываем курсор и подключение к базе данных
            cur.close()
            conn.close()

            # Возвращаем результат в шаблон
            return render_template('nodes_details.html', upper_node=upper_node,
                                   intermediate_nodes=intermediate_nodes, lowest_nodes=lowest_nodes)

        except ValueError:
            # Обрабатываем ошибку в случае некорректного node_id
            return "Ошибка: Некорректный node_id"

    else:
        # Если node_id не передан, отобразим страницу без данных
        return render_template('nodes_details.html')


def compute_weight_for_node(cursor, upper_node_id, current_node_id):
    # Запрос для получения всех связей между верхним узлом и текущим узлом
    cursor.execute('''WITH RECURSIVE Path AS (
                        SELECT upperNodeName, lowerNodeName, weight
                        FROM links
                        WHERE upperNodeName = %s AND lowerNodeName = %s
                        UNION
                        SELECT l.upperNodeName, l.lowerNodeName, l.weight
                        FROM Path p
                        JOIN links l ON p.lowerNodeName = l.upperNodeName
                    )
                    SELECT weight FROM Path''', (upper_node_id, current_node_id))

    # Получаем все найденные строки
    rows = cursor.fetchall()
    total_weight = 1

    # Перемножаем веса по всем найденным связям
    for row in rows:
        total_weight *= row[0]

    return total_weight


def get_intermediate_and_lowest_nodes(cursor, node_id, current_weight=1, node_name=None, node_description=None, level=0):
    # Запрос на получение нижестоящих узлов и их связей
    cursor.execute('''
        SELECT nodes.id, nodes.nodeName, nodes.nodeDescription, links.weight
        FROM nodes
        JOIN links ON nodes.id = links.lowerNodeName
        WHERE links.upperNodeName = %s
    ''', (node_id,))

    lower_nodes = cursor.fetchall()
    intermediate_nodes = []
    lowest_nodes = []

    if not lower_nodes:
        # Если нет нижестоящих узлов, текущий узел считается крайне низким узлом
        lowest_nodes.append((node_id, node_name, node_description, current_weight))
    else:
        # Обрабатываем нижестоящие узлы
        for node in lower_nodes:
            lower_node_id, node_name, node_description, link_weight = node
            total_weight = current_weight * link_weight

            # Рекурсивно получаем узлы для текущего нижестоящего узла
            inter_nodes, low_nodes = get_intermediate_and_lowest_nodes(
                cursor, lower_node_id, total_weight, node_name=node_name, node_description=node_description, level=level + 1
            )

            # Если текущий узел имеет нижестоящие узлы, добавляем его в промежуточные узлы
            if inter_nodes:
                intermediate_nodes.append((lower_node_id, node_name, node_description, total_weight))

            # Добавляем найденные узлы в списки
            intermediate_nodes.extend(inter_nodes)
            lowest_nodes.extend(low_nodes)

    return intermediate_nodes, lowest_nodes

