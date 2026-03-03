from flask import Flask, render_template, request, jsonify
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Text
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from contextlib import contextmanager
from datetime import datetime, timedelta
import os
import json

try:
    import anthropic
    _HAS_ANTHROPIC = True
except ImportError:
    _HAS_ANTHROPIC = False

from dotenv import load_dotenv
load_dotenv()

app = Flask(__name__)
app.secret_key = os.environ.get('FLASK_SECRET_KEY', 'stockpilot-dev-key')

DATABASE_URL = 'sqlite:///stockpilot.db'
engine = create_engine(DATABASE_URL)


class Base(DeclarativeBase):
    pass


class Supplier(Base):
    __tablename__ = 'suppliers'
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    contact_name = Column(String(100))
    email = Column(String(100))
    lead_days = Column(Integer, default=3)


class Item(Base):
    __tablename__ = 'items'
    id = Column(Integer, primary_key=True)
    sku = Column(String(20), unique=True)
    name = Column(String(200), nullable=False)
    category = Column(String(50))
    unit = Column(String(30), default='unit')
    quantity = Column(Integer, default=0)
    reorder_threshold = Column(Integer, default=10)
    reorder_qty = Column(Integer, default=20)
    supplier_id = Column(Integer)
    unit_cost = Column(Float, default=0.0)


class Transaction(Base):
    __tablename__ = 'transactions'
    id = Column(Integer, primary_key=True)
    item_id = Column(Integer)
    type = Column(String(20))       # intake | usage | adjustment
    quantity = Column(Integer)      # positive = intake, negative = usage
    note = Column(Text)
    ts = Column(DateTime, default=datetime.utcnow)


Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)


@contextmanager
def db():
    s = Session()
    try:
        yield s
        s.commit()
    except Exception:
        s.rollback()
        raise
    finally:
        s.close()


def get_status(qty, threshold):
    if qty <= 0:
        return 'out'
    if qty <= threshold:
        return 'low'
    return 'ok'


def item_dict(item):
    status = get_status(item.quantity, item.reorder_threshold)
    fill = min(100, round((item.quantity / max(1, item.reorder_threshold * 2)) * 100))
    return {
        'id': item.id,
        'sku': item.sku,
        'name': item.name,
        'category': item.category,
        'unit': item.unit,
        'quantity': item.quantity,
        'reorder_threshold': item.reorder_threshold,
        'reorder_qty': item.reorder_qty,
        'unit_cost': item.unit_cost,
        'supplier_id': item.supplier_id,
        'status': status,
        'fill_pct': fill,
    }


def seed():
    with db() as s:
        if s.query(Item).count() > 0:
            return

        suppliers = [
            Supplier(name='Pacific Coast Roasters', contact_name='Marco T.', email='orders@pcroasters.com', lead_days=5),
            Supplier(name='Dairy Direct Supply', contact_name='Kim R.', email='kim@dairydirect.com', lead_days=2),
            Supplier(name='Harbor Box Co.', contact_name='James L.', email='james@harborbox.co', lead_days=3),
            Supplier(name='Pro Clean Systems', contact_name='Sara V.', email='supply@proclean.com', lead_days=4),
        ]
        s.add_all(suppliers)
        s.flush()
        sup = {sup.name: sup.id for sup in suppliers}

        items = [
            # Beverages
            Item(sku='BEV-001', name='Ethiopian Yirgacheffe Beans', category='Beverages', unit='bag', quantity=12, reorder_threshold=5, reorder_qty=20, supplier_id=sup['Pacific Coast Roasters'], unit_cost=14.50),
            Item(sku='BEV-002', name='Sumatra Dark Roast Beans', category='Beverages', unit='bag', quantity=8, reorder_threshold=4, reorder_qty=15, supplier_id=sup['Pacific Coast Roasters'], unit_cost=13.00),
            Item(sku='BEV-003', name='House Blend Beans', category='Beverages', unit='bag', quantity=18, reorder_threshold=8, reorder_qty=30, supplier_id=sup['Pacific Coast Roasters'], unit_cost=11.50),
            Item(sku='BEV-004', name='Oat Milk', category='Beverages', unit='carton', quantity=24, reorder_threshold=10, reorder_qty=24, supplier_id=sup['Dairy Direct Supply'], unit_cost=2.80),
            Item(sku='BEV-005', name='Whole Milk', category='Beverages', unit='gallon', quantity=4, reorder_threshold=8, reorder_qty=12, supplier_id=sup['Dairy Direct Supply'], unit_cost=4.25),
            Item(sku='BEV-006', name='2% Milk', category='Beverages', unit='gallon', quantity=3, reorder_threshold=6, reorder_qty=12, supplier_id=sup['Dairy Direct Supply'], unit_cost=3.80),
            Item(sku='BEV-007', name='Vanilla Syrup', category='Beverages', unit='bottle', quantity=5, reorder_threshold=4, reorder_qty=8, supplier_id=sup['Pacific Coast Roasters'], unit_cost=7.50),
            Item(sku='BEV-008', name='Caramel Syrup', category='Beverages', unit='bottle', quantity=0, reorder_threshold=4, reorder_qty=8, supplier_id=sup['Pacific Coast Roasters'], unit_cost=7.50),
            Item(sku='BEV-009', name='Hazelnut Syrup', category='Beverages', unit='bottle', quantity=8, reorder_threshold=3, reorder_qty=6, supplier_id=sup['Pacific Coast Roasters'], unit_cost=7.50),
            # Packaging
            Item(sku='PKG-001', name='8oz Hot Cups', category='Packaging', unit='sleeve (50)', quantity=150, reorder_threshold=100, reorder_qty=200, supplier_id=sup['Harbor Box Co.'], unit_cost=0.08),
            Item(sku='PKG-002', name='12oz Hot Cups', category='Packaging', unit='sleeve (50)', quantity=280, reorder_threshold=200, reorder_qty=400, supplier_id=sup['Harbor Box Co.'], unit_cost=0.09),
            Item(sku='PKG-003', name='16oz Hot Cups', category='Packaging', unit='sleeve (50)', quantity=85, reorder_threshold=150, reorder_qty=300, supplier_id=sup['Harbor Box Co.'], unit_cost=0.10),
            Item(sku='PKG-004', name='Cup Lids (Universal)', category='Packaging', unit='pack (100)', quantity=40, reorder_threshold=20, reorder_qty=50, supplier_id=sup['Harbor Box Co.'], unit_cost=0.04),
            Item(sku='PKG-005', name='Paper Bags (Small)', category='Packaging', unit='bundle (100)', quantity=65, reorder_threshold=50, reorder_qty=100, supplier_id=sup['Harbor Box Co.'], unit_cost=0.12),
            Item(sku='PKG-006', name='Paper Bags (Large)', category='Packaging', unit='bundle (100)', quantity=28, reorder_threshold=40, reorder_qty=100, supplier_id=sup['Harbor Box Co.'], unit_cost=0.18),
            Item(sku='PKG-007', name='Napkins', category='Packaging', unit='pack (500)', quantity=10, reorder_threshold=15, reorder_qty=30, supplier_id=sup['Harbor Box Co.'], unit_cost=3.20),
            # Supplies
            Item(sku='SUP-001', name='Coffee Filters #4', category='Supplies', unit='box (100)', quantity=85, reorder_threshold=50, reorder_qty=100, supplier_id=sup['Harbor Box Co.'], unit_cost=0.04),
            Item(sku='SUP-002', name='Espresso Machine Cleaning Tabs', category='Supplies', unit='pack', quantity=2, reorder_threshold=5, reorder_qty=10, supplier_id=sup['Pro Clean Systems'], unit_cost=18.00),
            Item(sku='SUP-003', name='Descaler Solution', category='Supplies', unit='bottle', quantity=4, reorder_threshold=3, reorder_qty=6, supplier_id=sup['Pro Clean Systems'], unit_cost=12.50),
            Item(sku='SUP-004', name='Dish Soap', category='Supplies', unit='bottle', quantity=8, reorder_threshold=4, reorder_qty=8, supplier_id=sup['Pro Clean Systems'], unit_cost=3.50),
            Item(sku='SUP-005', name='Paper Towel Rolls', category='Supplies', unit='roll', quantity=18, reorder_threshold=10, reorder_qty=24, supplier_id=sup['Pro Clean Systems'], unit_cost=1.20),
            Item(sku='SUP-006', name='Nitrile Gloves', category='Supplies', unit='box (100)', quantity=6, reorder_threshold=4, reorder_qty=8, supplier_id=sup['Pro Clean Systems'], unit_cost=8.50),
            # Equipment
            Item(sku='EQP-001', name='Portafilter Baskets (Double)', category='Equipment', unit='unit', quantity=4, reorder_threshold=2, reorder_qty=4, supplier_id=sup['Pacific Coast Roasters'], unit_cost=22.00),
            Item(sku='EQP-002', name='Steam Wand Tips', category='Equipment', unit='unit', quantity=3, reorder_threshold=2, reorder_qty=4, supplier_id=sup['Pacific Coast Roasters'], unit_cost=15.00),
            Item(sku='EQP-003', name='Group Head Gaskets', category='Equipment', unit='unit', quantity=6, reorder_threshold=4, reorder_qty=8, supplier_id=sup['Pacific Coast Roasters'], unit_cost=8.00),
        ]
        s.add_all(items)
        s.flush()

        sku_to_id = {i.sku: i.id for i in items}
        now = datetime.utcnow()

        history = [
            ('BEV-003', 'usage', -3, 'Morning rush', -7),
            ('BEV-005', 'usage', -2, 'Morning service', -7),
            ('PKG-002', 'usage', -12, 'Daily cups', -7),
            ('BEV-003', 'usage', -4, 'Busy Saturday', -6),
            ('BEV-006', 'usage', -3, 'Milk service', -6),
            ('BEV-008', 'intake', 8, 'Caramel syrup delivery', -6),
            ('PKG-001', 'usage', -8, '8oz cups weekend', -6),
            ('BEV-001', 'usage', -2, 'Sunday morning', -5),
            ('BEV-007', 'intake', 6, 'Vanilla syrup restock', -5),
            ('PKG-003', 'usage', -20, '16oz cups — football crowd', -5),
            ('BEV-003', 'usage', -3, 'Weekday service', -4),
            ('BEV-005', 'usage', -2, 'Milk — am service', -4),
            ('BEV-008', 'usage', -4, 'Caramel latte special', -4),
            ('SUP-001', 'usage', -5, 'Filter change', -4),
            ('BEV-002', 'usage', -2, 'Sumatra pour-overs', -3),
            ('BEV-008', 'usage', -4, 'Caramel special day 2', -3),
            ('PKG-006', 'usage', -15, 'Retail bean bag sales', -3),
            ('SUP-002', 'usage', -3, 'Weekly machine clean', -3),
            ('BEV-003', 'usage', -3, 'House blend pm service', -2),
            ('BEV-005', 'usage', -1, 'Last whole milk gallon', -2),
            ('BEV-006', 'usage', -2, '2% milk running low', -2),
            ('PKG-007', 'usage', -5, 'Floor napkin restock', -2),
            ('BEV-001', 'usage', -2, 'Yirgacheffe pour-over trend', -1),
            ('BEV-003', 'usage', -3, 'Morning service', -1),
            ('PKG-003', 'usage', -30, '16oz takeout peak', -1),
            ('SUP-002', 'usage', -3, 'Weekly machine clean', -1),
        ]

        for sku, typ, qty, note, day in history:
            if sku in sku_to_id:
                s.add(Transaction(
                    item_id=sku_to_id[sku],
                    type=typ,
                    quantity=qty,
                    note=note,
                    ts=now + timedelta(days=day),
                ))


seed()


# ── Routes ──────────────────────────────────────────────────────────────────

@app.route('/')
def index():
    with db() as s:
        items = s.query(Item).order_by(Item.category, Item.name).all()
        data = [item_dict(i) for i in items]
        categories = sorted(set(i['category'] for i in data))
        counts = {'ok': 0, 'low': 0, 'out': 0}
        for i in data:
            counts[i['status']] += 1
        stats = {
            'total': len(data),
            'ok': counts['ok'],
            'low': counts['low'],
            'out': counts['out'],
            'alerts': counts['low'] + counts['out'],
        }
    return render_template('index.html',
                           items=data,
                           stats=stats,
                           categories=categories)


@app.route('/api/items')
def api_items():
    cat = request.args.get('category', 'all')
    status_f = request.args.get('status', 'all')
    with db() as s:
        q = s.query(Item).order_by(Item.category, Item.name)
        if cat != 'all':
            q = q.filter(Item.category == cat)
        items = [item_dict(i) for i in q.all()]
        if status_f != 'all':
            items = [i for i in items if i['status'] == status_f]
    return jsonify(items)


@app.route('/api/items/<int:item_id>/intake', methods=['POST'])
def intake(item_id):
    data = request.json or {}
    qty = int(data.get('quantity', 0))
    note = data.get('note', 'Manual intake')
    if qty <= 0:
        return jsonify({'error': 'Quantity must be positive'}), 400
    with db() as s:
        item = s.get(Item, item_id)
        if not item:
            return jsonify({'error': 'Not found'}), 404
        item.quantity += qty
        s.add(Transaction(item_id=item_id, type='intake', quantity=qty, note=note))
        return jsonify(item_dict(item))


@app.route('/api/items/<int:item_id>/usage', methods=['POST'])
def usage(item_id):
    data = request.json or {}
    qty = int(data.get('quantity', 0))
    note = data.get('note', 'Manual usage')
    if qty <= 0:
        return jsonify({'error': 'Quantity must be positive'}), 400
    with db() as s:
        item = s.get(Item, item_id)
        if not item:
            return jsonify({'error': 'Not found'}), 404
        item.quantity = max(0, item.quantity - qty)
        s.add(Transaction(item_id=item_id, type='usage', quantity=-qty, note=note))
        return jsonify(item_dict(item))


@app.route('/api/items/<int:item_id>/history')
def history(item_id):
    with db() as s:
        txns = (s.query(Transaction)
                .filter_by(item_id=item_id)
                .order_by(Transaction.ts.desc())
                .limit(20).all())
        return jsonify([{
            'id': t.id,
            'type': t.type,
            'quantity': t.quantity,
            'note': t.note,
            'ts': t.ts.strftime('%b %d, %Y %H:%M'),
        } for t in txns])


@app.route('/api/ai-summary')
def ai_summary():
    api_key = os.environ.get('ANTHROPIC_API_KEY', '')
    with db() as s:
        since = datetime.utcnow() - timedelta(days=7)
        txns = s.query(Transaction).filter(Transaction.ts >= since).all()
        items = {i.id: i for i in s.query(Item).all()}

        usage_by_item = {}
        for t in txns:
            if t.type == 'usage' and t.item_id in items:
                name = items[t.item_id].name
                usage_by_item[name] = usage_by_item.get(name, 0) + abs(t.quantity)

        low_items = [
            {'name': i.name, 'qty': i.quantity, 'threshold': i.reorder_threshold, 'status': get_status(i.quantity, i.reorder_threshold)}
            for i in items.values()
            if get_status(i.quantity, i.reorder_threshold) in ('low', 'out')
        ]

    if not api_key or not _HAS_ANTHROPIC:
        top = sorted(usage_by_item.items(), key=lambda x: x[1], reverse=True)[:3]
        demo = (
            "**Weekly Ops Summary — Harbor Coffee Co.**\n\n"
            f"**High-velocity items this week:** {', '.join(f'{n} ({u} units)' for n, u in top)}.\n\n"
            f"**{len(low_items)} items need attention:** {', '.join(i['name'] for i in low_items[:5])}.\n\n"
            "**Recommended actions:**\n"
            "- Place immediate order for Caramel Syrup (OUT) and dairy milk (LOW) — both are customer-facing.\n"
            "- 16oz Hot Cups trending down fast — reorder before Friday rush.\n"
            "- Espresso Machine Cleaning Tabs at 2 packs — schedule restock; covers ~1 cycle.\n\n"
            "*[AI summary requires ANTHROPIC_API_KEY — showing demo output]*"
        )
        return jsonify({'summary': demo, 'demo': True})

    client = anthropic.Anthropic(api_key=api_key)
    prompt = (
        "Harbor Coffee Co. Supply Room — Weekly Ops Report\n\n"
        f"Usage this week (item: units used):\n{json.dumps(usage_by_item, indent=2)}\n\n"
        f"Items at or below reorder threshold:\n{json.dumps(low_items, indent=2)}\n\n"
        "Write a 150-200 word plain-English weekly ops summary. Include:\n"
        "1. Top 3 highest-usage items this week\n"
        "2. Items needing immediate reorder (OUT first, then LOW)\n"
        "3. Any anomalies (e.g. unusually high usage spikes)\n"
        "4. Three bullet action items\n\n"
        "Use markdown bold for headers. Be direct and operational in tone."
    )
    resp = client.messages.create(
        model=os.environ.get('GENERATOR_MODEL', 'claude-haiku-4-5-20251001'),
        max_tokens=400,
        messages=[{'role': 'user', 'content': prompt}],
    )
    return jsonify({'summary': resp.content[0].text, 'demo': False})


@app.route('/api/reset', methods=['POST'])
def reset():
    with db() as s:
        s.query(Transaction).delete()
        s.query(Item).delete()
        s.query(Supplier).delete()
    seed()
    return jsonify({'ok': True})


if __name__ == '__main__':
    app.run(debug=True, port=5001)
