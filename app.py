from sqlalchemy import Column, Integer, String, Float, ForeignKey, Date, Enum, create_engine, func
from sqlalchemy.orm import relationship, sessionmaker, declarative_base, joinedload
from flask import Flask, jsonify, request, render_template, redirect, url_for, send_file
from datetime import datetime
import matplotlib.pyplot as plt
import base64
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase import pdfmetrics
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
from flask import send_file
import io

Base = declarative_base()


class WoodType(Base):
    __tablename__ = 'wood_types'

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    description = Column(String, nullable=True)


class PlywoodSheet(Base):
    __tablename__ = 'plywood_sheets'

    id = Column(Integer, primary_key=True)
    wood_type_id = Column(Integer, ForeignKey('wood_types.id'), nullable=False)
    thickness = Column(Float, nullable=False)
    name = Column(String, nullable=False)

    wood_type = relationship("WoodType", backref="plywood_sheets")


class Puzzle(Base):
    __tablename__ = 'puzzles'

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    piece_count = Column(Integer, nullable=False)
    plywood_sheet_id = Column(Integer, ForeignKey('plywood_sheets.id'), nullable=False)
    image_path = Column(String, nullable=True)

    plywood_sheet = relationship("PlywoodSheet", backref="puzzles")


class Client(Base):
    __tablename__ = 'clients'

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)


class Order(Base):
    __tablename__ = 'orders'

    id = Column(Integer, primary_key=True)
    client_id = Column(Integer, ForeignKey('clients.id'), nullable=False)
    status = Column(
        Enum('Черновик', 'Подтверждён', 'На производстве', 'Готов к отгрузке', 'Отгружен клиенту', name='order_status'),
        nullable=False, default='Черновик')
    order_date = Column(Date, default=datetime.now, nullable=False)
    delivery_date = Column(Date, nullable=True)

    client = relationship("Client", backref="orders")


class OrderItem(Base):
    __tablename__ = 'order_items'

    id = Column(Integer, primary_key=True)
    order_id = Column(Integer, ForeignKey('orders.id'), nullable=False)
    puzzle_id = Column(Integer, ForeignKey('puzzles.id'), nullable=False)
    quantity = Column(Integer, nullable=False)
    price = Column(Float, nullable=False)
    total = Column(Float, nullable=False)

    order = relationship("Order", backref="order_items")
    puzzle = relationship("Puzzle", backref="order_items")


class ProductionTask(Base):
    __tablename__ = 'production_tasks'

    id = Column(Integer, primary_key=True)
    order_id = Column(Integer, ForeignKey('orders.id'), nullable=False)
    status = Column(Enum('Принят', 'Выполнен', name='production_task_status'), nullable=False, default='Принят')

    order = relationship("Order", backref="production_tasks")


class Shipment(Base):
    __tablename__ = 'shipments'

    id = Column(Integer, primary_key=True)
    order_id = Column(Integer, ForeignKey('orders.id'), nullable=False)
    shipment_date = Column(Date, default=datetime.now, nullable=False)

    order = relationship("Order", backref="shipments")


class Price(Base):
    __tablename__ = 'prices'

    id = Column(Integer, primary_key=True)
    puzzle_id = Column(Integer, ForeignKey('puzzles.id'), nullable=False)
    price = Column(Float, nullable=False)
    effective_date = Column(Date, default=datetime.now, nullable=False)

    puzzle = relationship("Puzzle", backref="prices")


engine = create_engine('sqlite:///puzzle_factory.db', echo=True)
Base.metadata.create_all(engine)

Session = sessionmaker(bind=engine)
session = Session()

app = Flask(__name__)


@app.route('/')
def home():
    return render_template('index.html')


@app.route('/wood_types_page', methods=['GET', 'POST'])
def wood_types_page():
    if request.method == 'POST':
        name = request.form['name']
        description = request.form['description']
        new_wood_type = WoodType(name=name, description=description)
        session.add(new_wood_type)
        session.commit()
        return redirect(url_for('wood_types_page'))
    wood_types = session.query(WoodType).all()
    return render_template('wood_types.html', wood_types=wood_types)


@app.route('/plywood_sheets_page', methods=['GET', 'POST'])
def plywood_sheets_page():
    if request.method == 'POST':
        name = request.form['name']
        wood_type_id = request.form['wood_type_id']
        thickness = float(request.form['thickness'])
        new_plywood_sheet = PlywoodSheet(name=name, wood_type_id=wood_type_id, thickness=thickness)
        session.add(new_plywood_sheet)
        session.commit()
        return redirect(url_for('plywood_sheets_page'))
    plywood_sheets = session.query(PlywoodSheet).all()
    wood_types = session.query(WoodType).all()
    return render_template('plywood_sheets.html', plywood_sheets=plywood_sheets, wood_types=wood_types)


@app.route('/puzzles_page', methods=['GET', 'POST'])
def puzzles_page():
    if request.method == 'POST':
        name = request.form['name']
        piece_count = int(request.form['piece_count'])
        plywood_sheet_id = int(request.form['plywood_sheet_id'])
        image_path = request.form['image_path']
        new_puzzle = Puzzle(name=name, piece_count=piece_count, plywood_sheet_id=plywood_sheet_id,
                            image_path=image_path)
        session.add(new_puzzle)
        session.commit()
        return redirect(url_for('puzzles_page'))
    puzzles = session.query(Puzzle).all()
    plywood_sheets = session.query(PlywoodSheet).all()
    return render_template('puzzles.html', puzzles=puzzles, plywood_sheets=plywood_sheets)


@app.route('/clients_page', methods=['GET', 'POST'])
def clients_page():
    if request.method == 'POST':
        name = request.form['name']
        new_client = Client(name=name)
        session.add(new_client)
        session.commit()
        return redirect(url_for('clients_page'))
    clients = session.query(Client).all()
    return render_template('clients.html', clients=clients)


@app.route('/puzzle_card/<int:puzzle_id>', methods=['GET'])
def puzzle_card(puzzle_id):
    puzzle = session.query(Puzzle).filter(Puzzle.id == puzzle_id).first()
    if not puzzle:
        return "Puzzle not found", 404
    return render_template('puzzle_card.html', puzzle=puzzle)


@app.route('/price_list', methods=['GET', 'POST'])
def price_list_page():
    puzzles = session.query(Puzzle).all()
    prices = session.query(Price).order_by(Price.effective_date.desc()).distinct(Price.puzzle_id).all()

    price_data = []
    for price in prices:
        puzzle = next((p for p in puzzles if p.id == price.puzzle_id), None)
        if puzzle:
            price_data.append({
                'name': puzzle.name,
                'price': price.price,
                'date': price.effective_date
            })

    return render_template('price_list.html', price_data=price_data, puzzles=puzzles)


@app.route('/price_list/update', methods=['POST'])
def update_price():
    puzzle_id = request.form.get('puzzle_id')
    new_price = request.form.get('price')

    if not puzzle_id or not new_price:
        return "Invalid data", 400

    existing_price = session.query(Price).filter(Price.puzzle_id == puzzle_id).order_by(
        Price.effective_date.desc()).first()

    if existing_price:
        existing_price.price = float(new_price)
        existing_price.effective_date = datetime.now()
    else:
        new_price_entry = Price(
            puzzle_id=puzzle_id,
            price=float(new_price),
            effective_date=datetime.now()
        )
        session.add(new_price_entry)

    session.commit()
    return redirect(url_for('price_list_page'))


pdfmetrics.registerFont(TTFont('DejaVuSans', 'static/fonts/DejaVuSans.ttf'))


@app.route('/price_list/export', methods=['GET'])
def export_price_list():
    pdf_buffer = io.BytesIO()
    pdf = SimpleDocTemplate(pdf_buffer, pagesize=letter)
    elements = []

    styles = {
        'Heading1': ParagraphStyle('Heading1', fontSize=14, spaceAfter=12, fontName='DejaVuSans'),
        'Normal': ParagraphStyle('Normal', spaceAfter=6, fontName='DejaVuSans')
    }

    elements.append(Paragraph("Прайс-лист", styles['Heading1']))

    data = [["Название товара", "Цена", "Дата изменения"]]
    prices = session.query(Price).order_by(Price.effective_date.desc()).distinct(Price.puzzle_id).all()
    puzzles = session.query(Puzzle).all()
    for price in prices:
        puzzle = next((p for p in puzzles if p.id == price.puzzle_id), None)
        if puzzle:
            data.append([puzzle.name, f"{price.price} руб.", price.effective_date.strftime('%Y-%m-%d')])

    table = Table(data, hAlign='LEFT')
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (1, 1), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'DejaVuSans'),
        ('FONTNAME', (0, 1), (-1, -1), 'DejaVuSans'),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
    ]))
    elements.append(table)

    pdf.build(elements)
    pdf_buffer.seek(0)

    return send_file(pdf_buffer, as_attachment=True, download_name="price_list.pdf", mimetype="application/pdf")


@app.route('/clients', methods=['GET', 'POST'])
def manage_clients():
    if request.method == 'POST':
        client_id = request.form.get('client_id')
        if client_id:
            client = session.query(Client).filter(Client.id == client_id).first()
            client.name = request.form['name']
        else:
            name = request.form['name']
            new_client = Client(name=name)
            session.add(new_client)
        session.commit()
        return redirect(url_for('manage_clients'))

    clients = session.query(Client).all()
    return render_template('clients.html', clients=clients)


@app.route('/orders', methods=['GET', 'POST'])
def manage_orders():
    if request.method == 'POST':
        order_id = request.form.get('order_id')
        new_status = request.form.get('status')

        if order_id and new_status:
            order = session.query(Order).filter(Order.id == int(order_id)).first()
            if order:
                order.status = new_status
                session.commit()
            return redirect(url_for('manage_orders'))

        client_id = request.form.get('client_id')
        delivery_date_str = request.form.get('delivery_date')
        items = request.form.getlist('item')
        quantities = request.form.getlist('quantity')

        if client_id and delivery_date_str and items and quantities:
            delivery_date = datetime.strptime(delivery_date_str, '%Y-%m-%d').date()
            new_order = Order(
                client_id=int(client_id),
                delivery_date=delivery_date,
                order_date=datetime.now(),
                status='Черновик'
            )
            session.add(new_order)
            session.commit()

            for item_id, quantity in zip(items, quantities):
                item = OrderItem(
                    order_id=new_order.id,
                    puzzle_id=int(item_id),
                    quantity=int(quantity),
                    price=session.query(Price)
                    .filter(Price.puzzle_id == int(item_id))
                    .order_by(Price.effective_date.desc())
                    .first().price,
                    total=int(quantity) * session.query(Price)
                    .filter(Price.puzzle_id == int(item_id))
                    .order_by(Price.effective_date.desc())
                    .first().price
                )
                session.add(item)
            session.commit()
        return redirect(url_for('manage_orders'))

    orders = session.query(Order).options(joinedload(Order.client)).all()
    clients = session.query(Client).all()
    puzzles = session.query(Puzzle).all()

    return render_template('orders.html', orders=orders, clients=clients, puzzles=puzzles)


@app.route('/order/<int:order_id>', methods=['GET', 'POST'])
def order_page(order_id):
    order = session.query(Order).filter(Order.id == order_id).first()
    if not order:
        return "Order not found", 404

    if request.method == 'POST':
        puzzle_id = int(request.form['puzzle_id'])
        quantity = int(request.form['quantity'])

        price_entry = session.query(Price).filter(Price.puzzle_id == puzzle_id).order_by(
            Price.effective_date.desc()).first()
        price = price_entry.price if price_entry else 0.0
        total = price * quantity

        new_item = OrderItem(order_id=order.id, puzzle_id=puzzle_id, quantity=quantity, price=price, total=total)
        session.add(new_item)
        session.commit()
        return redirect(url_for('order_page', order_id=order_id))

    puzzles = session.query(Puzzle).all()
    return render_template('order.html', order=order, puzzles=puzzles)


@app.route('/order/<int:order_id>/invoice', methods=['GET'])
def generate_invoice(order_id):
    order = session.query(Order).filter(Order.id == order_id).first()
    if not order:
        return "Order not found", 404

    pdf_buffer = io.BytesIO()
    pdf = SimpleDocTemplate(pdf_buffer, pagesize=letter)
    elements = []

    styles = {
        'Heading1': ParagraphStyle('Heading1', fontSize=14, spaceAfter=12, fontName='DejaVuSans'),
        'Normal': ParagraphStyle('Normal', spaceAfter=6, fontName='DejaVuSans')
    }

    elements.append(Paragraph(f"Накладная для заказа №{order.id}", styles['Heading1']))
    elements.append(Paragraph(f"Клиент: {order.client.name}", styles['Normal']))
    elements.append(Paragraph(f"Дата заказа: {order.order_date}", styles['Normal']))
    elements.append(Paragraph(f"Дата выполнения: {order.delivery_date or 'Не указана'}", styles['Normal']))

    data = [["Название товара", "Количество", "Цена", "Сумма"]]
    for item in order.order_items:
        data.append([item.puzzle.name, item.quantity, f"{item.price} руб.", f"{item.total} руб."])

    total = sum(item.total for item in order.order_items)
    data.append(["", "", "Общая сумма", f"{total} руб."])

    table = Table(data, hAlign='LEFT')
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (1, 1), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'DejaVuSans'),
        ('FONTNAME', (0, 1), (-1, -1), 'DejaVuSans'),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
    ]))
    elements.append(table)

    pdf.build(elements)
    pdf_buffer.seek(0)

    return send_file(pdf_buffer, as_attachment=True, download_name=f"invoice_order_{order.id}.pdf",
                     mimetype="application/pdf")


@app.route('/shipment/<int:shipment_id>/generate', methods=['GET'])
def generate_shipment_pdf(shipment_id):
    shipment = session.query(Shipment).filter(Shipment.id == shipment_id).first()
    if not shipment:
        return "Shipment not found", 404

    order = shipment.order
    if not order:
        return "Order not found", 404

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)

    styles = getSampleStyleSheet()
    styles['Normal'].fontName = 'DejaVuSans'
    styles['Title'].fontName = 'DejaVuSans'

    elements = []

    elements.append(Paragraph(f"Документ отгрузки №{shipment.id}", styles['Title']))
    elements.append(Paragraph(f"Клиент: {order.client.name}", styles['Normal']))
    elements.append(Paragraph(f"Дата отгрузки: {shipment.shipment_date}", styles['Normal']))
    elements.append(Paragraph(f"Дата заказа: {order.order_date}", styles['Normal']))

    data = [["Название товара", "Количество", "Цена", "Сумма"]]
    for item in order.order_items:
        data.append([item.puzzle.name, item.quantity, f"{item.price} руб.", f"{item.total} руб."])

    total = sum(item.total for item in order.order_items)
    data.append(["", "", "Общая сумма", f"{total} руб."])

    table = Table(data, hAlign='LEFT')
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'DejaVuSans'),
        ('FONTNAME', (0, 1), (-1, -1), 'DejaVuSans'),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    elements.append(table)

    doc.build(elements)
    buffer.seek(0)

    return send_file(buffer, as_attachment=True, download_name=f"shipment_{shipment.id}.pdf",
                     mimetype='application/pdf')


@app.route('/production_tasks', methods=['GET', 'POST'])
def production_tasks_page():
    if request.method == 'POST':
        order_id = int(request.form['order_id'])
        order = session.query(Order).filter(Order.id == order_id).first()
        order.status = 'На производстве'
        new_task = ProductionTask(order_id=order_id, status='Принят')
        session.add(new_task)
        session.commit()
        return redirect(url_for('production_tasks_page'))

    tasks = session.query(ProductionTask).all()
    orders = session.query(Order).filter(Order.status == 'Подтверждён').all()
    return render_template('production_tasks.html', tasks=tasks, orders=orders)


@app.route('/production_task/<int:task_id>/complete', methods=['POST'])
def complete_production_task(task_id):
    task = session.query(ProductionTask).filter(ProductionTask.id == task_id).first()
    if not task:
        return "Task not found", 404
    task.status = 'Выполнен'
    task.order.status = 'Готов к отгрузке'
    session.commit()
    return redirect(url_for('production_tasks_page'))


@app.route('/shipments', methods=['GET', 'POST'])
def shipments_page():
    if request.method == 'POST':
        order_id = int(request.form['order_id'])
        new_shipment = Shipment(order_id=order_id, shipment_date=datetime.now())
        order = session.query(Order).filter(Order.id == order_id).first()
        order.status = 'Отгружен клиенту'
        session.add(new_shipment)
        session.commit()
        return redirect(url_for('shipments_page'))

    shipments = session.query(Shipment).all()
    orders = session.query(Order).filter(Order.status == 'Готов к отгрузке').all()
    return render_template('shipments.html', shipments=shipments, orders=orders)


@app.route('/analytics', methods=['GET'])
def analytics_page():
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')

    query = session.query(
        Puzzle.name,
        func.sum(OrderItem.quantity).label('total_quantity'),
        func.sum(OrderItem.total).label('total_sales')
    ).join(OrderItem).join(Order).filter(Order.status == 'Отгружен клиенту')

    if start_date:
        query = query.filter(Order.order_date >= start_date)
    if end_date:
        query = query.filter(Order.order_date <= end_date)

    sales_data = query.group_by(Puzzle.name).all()

    def generate_sales_chart(sales_data):
        puzzles = [row[0] for row in sales_data]
        sales = [row[2] for row in sales_data]

        plt.figure(figsize=(10, 6))
        plt.bar(puzzles, sales, color='skyblue')
        plt.xlabel('Пазлы')
        plt.ylabel('Сумма продаж')
        plt.title('Продажи по пазлам')

        img = io.BytesIO()
        plt.savefig(img, format='png')
        img.seek(0)
        chart_url = base64.b64encode(img.getvalue()).decode('utf8')
        plt.close()

        return f"data:image/png;base64,{chart_url}"

    chart_url = generate_sales_chart(sales_data)

    production_tasks = session.query(
        ProductionTask.id,
        Puzzle.name,
        Order.order_date,
        ProductionTask.status,
        Order.delivery_date
    ).join(Order).join(OrderItem).join(Puzzle).filter(
        ProductionTask.status == 'Принят'
    ).all()

    today = datetime.now().date()
    for task in production_tasks:
        task_color = "red" if task[4] and (task[4] - today).days <= 1 else "black"

    return render_template(
        'analytics.html',
        sales_data=sales_data,
        chart_url=chart_url,
        production_tasks=production_tasks,
        today=today,
        start_date=start_date,
        end_date=end_date
    )


@app.route('/plywood_sheet/<int:sheet_id>', methods=['GET'])
def plywood_sheet_details(sheet_id):
    sheet = session.query(PlywoodSheet).filter(PlywoodSheet.id == sheet_id).first()
    if not sheet:
        return "Plywood sheet not found", 404
    return render_template('plywood_sheet_details.html', sheet=sheet)


if __name__ == "__main__":
    app.run(debug=True)
