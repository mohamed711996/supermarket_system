import streamlit as st
import psycopg2
import pandas as pd
from io import BytesIO
from datetime import datetime
# ========================
# اتصال قاعدة البيانات
# ========================
def get_connection():
    return psycopg2.connect(
        host="aws-1-eu-north-1.pooler.supabase.com",
        port="6543",
        database="postgres",
        user="postgres.npqbudrksqjriqukgyku",
        password="123!bee.com"
    )

# ========================
# رفع الأصناف من Excel
# ========================
def upload_products(file):
    df = pd.read_excel(file)
    conn = get_connection()
    cur = conn.cursor()
    for _, row in df.iterrows():
        cur.execute("""
            INSERT INTO products (productname, category, unit, currentprice, barcode, stock)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT (barcode) DO UPDATE 
            SET productname = EXCLUDED.productname,
                category = EXCLUDED.category,
                unit = EXCLUDED.unit,
                currentprice = EXCLUDED.currentprice,
                stock = EXCLUDED.stock;
        """, (
            row['ProductName'], row['Category'], row['Unit'],
            float(row['CurrentPrice']), row['Barcode'], int(row['Stock'])
        ))
    conn.commit()
    conn.close()

# ========================
# تحميل Template Excel
# ========================
def download_template():
    output = BytesIO()
    df = pd.DataFrame(columns=["ProductName", "Category", "Unit", "CurrentPrice", "Barcode", "Stock"])
    df.to_excel(output, index=False)
    return output

# ========================
# واجهة Streamlit
# ========================
st.title("🛒 نظام إدارة السوبر ماركت")
menu = st.sidebar.selectbox("القائمة", ["المنتجات", "إضافة منتج يدوي", "المشتريات", "المبيعات", "المصروفات", "الشحن", "رفع من Excel", "التحليلات"])

# ========================
# إدارة وعرض المنتجات مع تعديل السعر والمخزون
# ========================
if menu == "المنتجات":
    st.subheader("إدارة المنتجات")
    conn = get_connection()
    df = pd.read_sql("SELECT * FROM products", conn)

    product_names = df['productname'].tolist()
    selected_product = st.selectbox("اختر المنتج لتعديله", product_names)

    if selected_product:
        product_info = df[df['productname'] == selected_product].iloc[0]
        
        new_price = st.number_input("سعر البيع الحالي", min_value=0.0, value=float(product_info['currentprice']))
        new_stock = st.number_input("المخزون الحالي", min_value=0, value=int(product_info['stock']))

        if st.button("تحديث المنتج"):
            cur = conn.cursor()
            cur.execute(
                "UPDATE products SET currentprice=%s, stock=%s WHERE productid=%s",
                (float(new_price), int(new_stock), int(product_info['productid']))
            )
            conn.commit()
            st.success(f"✅ تم تحديث المنتج {selected_product} بنجاح")
    
    st.dataframe(df)
    conn.close()

# ========================
# إضافة منتج يدوي
# ========================
# ========================
# إضافة منتج يدوي مع اختيار فئة موجودة أو جديدة
# ========================
# ========================
# إضافة منتج يدوي مع اختيار فئة موجودة أو جديدة + Session State
# ========================
elif menu == "إضافة منتج يدوي":
    st.subheader("➕ إضافة / تعديل منتج")
    
    if "new_category" not in st.session_state:
        st.session_state.new_category = ""
    
    action = st.radio("اختر العملية", ["إضافة منتج جديد", "تعديل منتج موجود"])
    
    conn = get_connection()
    df_products = pd.read_sql("SELECT * FROM products", conn)
    df_categories = pd.read_sql("SELECT DISTINCT category FROM products", conn)
    conn.close()
    
    categories = df_categories['category'].tolist()
    
    if action == "إضافة منتج جديد":
        selected_category = st.selectbox("اختر فئة موجودة أو إضافة جديدة", ["-- فئة جديدة --"] + categories)
        
        if selected_category == "-- فئة جديدة --":
            st.session_state.new_category = st.text_input("أدخل اسم الفئة الجديدة", st.session_state.new_category)
            category = st.session_state.new_category
        else:
            category = selected_category
        
        productname = st.text_input("أدخل اسم المنتج")
        unit = st.text_input("الوحدة (علبة/كجم/قطعة...)")
        price = st.number_input("سعر البيع", min_value=0.0)
        stock = st.number_input("المخزون", min_value=0)
        barcode = st.text_input("الباركود")
        
        if st.button("إضافة المنتج"):
            if category.strip() == "" or productname.strip() == "" or barcode.strip() == "":
                st.error("❌ يجب إدخال اسم الفئة واسم المنتج والباركود")
            else:
                conn = get_connection()
                cur = conn.cursor()
                # تحقق إذا الباركود موجود بالفعل
                cur.execute("SELECT productid FROM products WHERE barcode=%s", (barcode,))
                existing = cur.fetchone()
                if existing:
                    st.error("❌ الباركود موجود بالفعل. استخدم تعديل منتج موجود")
                else:
                    cur.execute("""
                        INSERT INTO products (productname, category, unit, currentprice, barcode, stock)
                        VALUES (%s,%s,%s,%s,%s,%s)
                    """, (productname.strip(), category.strip(), unit, float(price), barcode.strip(), int(stock)))
                    conn.commit()
                    st.success(f"✅ تم إضافة المنتج {productname.strip()} تحت الفئة {category.strip()}")
                    st.session_state.new_category = ""  # تفريغ الفئة الجديدة بعد الإضافة
    
    else:  # تعديل منتج موجود
        barcodes = df_products['barcode'].tolist()
        selected_barcode = st.selectbox("اختر الباركود لتعديل المنتج", barcodes)
        if selected_barcode:
            product_info = df_products[df_products['barcode'] == selected_barcode].iloc[0]
            
            category = st.selectbox("الفئة", ["-- فئة جديدة --"] + categories, index=(categories.index(product_info['category'])+1 if product_info['category'] in categories else 0))
            if category == "-- فئة جديدة --":
                category = st.text_input("أدخل اسم الفئة الجديدة", value=product_info['category'])
            
            productname = st.text_input("اسم المنتج", value=product_info['productname'])
            unit = st.text_input("الوحدة", value=product_info['unit'])
            price = st.number_input("سعر البيع", value=float(product_info['currentprice']))
            stock = st.number_input("المخزون", value=int(product_info['stock']))
            barcode = st.text_input("الباركود", value=product_info['barcode'])
            
            if st.button("تحديث المنتج"):
                conn = get_connection()
                cur = conn.cursor()
                cur.execute("""
                    UPDATE products
                    SET productname=%s, category=%s, unit=%s, currentprice=%s, stock=%s, barcode=%s
                    WHERE barcode=%s
                """, (productname.strip(), category.strip(), unit, float(price), int(stock), barcode.strip(), selected_barcode))
                conn.commit()
                conn.close()
                st.success(f"✅ تم تحديث المنتج {productname.strip()} بنجاح")


# ========================
# تسجيل المشتريات - مع اختيار الفئة أولًا
# ========================
elif menu == "المشتريات":
    st.subheader("تسجيل عملية شراء - فاتورة متعددة منتجات")
    conn = get_connection()
    df_products = pd.read_sql("SELECT * FROM products", conn)

    categories = df_products['category'].unique().tolist()
    selected_category = st.selectbox("اختر الفئة", categories)

    if selected_category:
        products_in_cat = df_products[df_products['category'] == selected_category]
        selected_products = st.multiselect("اختر المنتجات", products_in_cat['productname'].tolist())

        purchase_details = []
        for pname in selected_products:
            product_info = products_in_cat[products_in_cat['productname'] == pname].iloc[0]
            qty_max = int(product_info['stock']) if int(product_info['stock']) > 0 else 100000
            qty = st.number_input(f"الكمية - {pname}", min_value=1, max_value=qty_max, key=f"buy_qty_{pname}")
            cost = st.number_input(f"سعر الشراء - {pname}", value=0.0, key=f"buy_price_{pname}")
            purchase_details.append((int(product_info['productid']), int(qty), float(cost)))

        if st.button("تسجيل الشراء"):
            cur = conn.cursor()
            for productid, qty, cost in purchase_details:
                cur.execute(
                    "INSERT INTO purchases (productid, quantitypurchased, costprice, purchasedate) VALUES (%s,%s,%s,NOW())",
                    (productid, qty, cost)
                )
                cur.execute(
                    "UPDATE products SET stock = stock + %s WHERE productid = %s",
                    (qty, productid)
                )
            conn.commit()
            st.success(f"✅ تم تسجيل شراء {len(purchase_details)} منتج/منتجات")
    conn.close()

# ========================
# تسجيل المبيعات - مع اختيار الفئة أولًا
# ========================
elif menu == "المبيعات":
    st.subheader("تسجيل عملية بيع - فاتورة متعددة منتجات")
    conn = get_connection()
    df_products = pd.read_sql("SELECT * FROM products", conn)

    categories = df_products['category'].unique().tolist()
    selected_category = st.selectbox("اختر الفئة", categories)

    if selected_category:
        products_in_cat = df_products[df_products['category'] == selected_category]
        selected_products = st.multiselect("اختر المنتجات", products_in_cat['productname'].tolist())

        sale_details = []
        for pname in selected_products:
            product_info = products_in_cat[products_in_cat['productname'] == pname].iloc[0]
            max_qty = int(product_info['stock'])
            if max_qty == 0:
                st.warning(f"⚠️ المنتج {pname} غير متوفر في المخزون")
                continue
            qty = st.number_input(f"الكمية - {pname}", min_value=1, max_value=max_qty, key=f"sell_qty_{pname}")
            price = st.number_input(f"سعر البيع - {pname}", value=float(product_info['currentprice']), key=f"sell_price_{pname}")
            sale_details.append((int(product_info['productid']), int(qty), float(price)))

        if st.button("تسجيل البيع"):
            cur = conn.cursor()
            for productid, qty, price in sale_details:
                cur.execute(
                    "INSERT INTO sales (productid, quantitysold, recordedsaleprice, saledate) VALUES (%s,%s,%s,NOW())",
                    (productid, qty, price)
                )
                cur.execute(
                    "UPDATE products SET stock = stock - %s WHERE productid = %s",
                    (qty, productid)
                )
            conn.commit()
            st.success(f"✅ تم تسجيل بيع {len(sale_details)} منتج/منتجات")
    conn.close()

# ========================
# تسجيل المصروفات
# ========================
elif menu == "المصروفات":
    st.subheader("تسجيل مصروف")
    type_exp = st.text_input("نوع المصروف")
    amount = st.number_input("المبلغ", min_value=1.0)
    notes = st.text_area("ملاحظات")
    if st.button("إضافة مصروف"):
        conn = get_connection()
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO expenses (expensetype, amount, notes, expensedate) VALUES (%s,%s,%s,NOW())",
            (type_exp, float(amount), notes)
        )
        conn.commit()
        conn.close()
        st.success("✅ تمت إضافة المصروف")

# ========================
# تسجيل الشحن
# ========================
elif menu == "الشحن":
    st.subheader("تسجيل عملية شحن")
    desc = st.text_input("الوصف")
    cost = st.number_input("التكلفة", min_value=1.0)
    if st.button("إضافة شحن"):
        conn = get_connection()
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO shipping (description, cost, shippingdate) VALUES (%s,%s,NOW())",
            (desc, float(cost))
        )
        conn.commit()
        conn.close()
        st.success("✅ تمت إضافة عملية الشحن")

# ========================
# رفع المنتجات من Excel
# ========================
elif menu == "رفع من Excel":
    st.subheader("رفع المنتجات من ملف Excel")
    file = st.file_uploader("اختار ملف Excel", type=["xlsx"])
    if file:
        upload_products(file)
        st.success("✅ تم رفع المنتجات بنجاح")

    st.download_button(
        label="📥 تحميل ملف Excel Template",
        data=download_template(),
        file_name="products_template.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

# ========================
# التحليلات مع فلتر من - إلى
# ========================


elif menu == "التحليلات":
    st.subheader("📊 تقارير وتحليلات - Overview")
    conn = get_connection()
    
    # اختيار التاريخ
    from_date = st.date_input("من تاريخ")
    to_date = st.date_input("إلى تاريخ")

    # تحويل التاريخ ليشمل اليوم كامل
    from_datetime = datetime.combine(from_date, datetime.min.time())
    to_datetime = datetime.combine(to_date, datetime.max.time())

    # إجمالي المبيعات
    sales = pd.read_sql("""
        SELECT SUM(quantitysold * recordedsaleprice) as total_sales
        FROM sales
        WHERE saledate BETWEEN %s AND %s
    """, conn, params=(from_datetime, to_datetime))

    # إجمالي المشتريات
    purchases = pd.read_sql("""
        SELECT SUM(quantitypurchased * costprice) as total_purchases
        FROM purchases
        WHERE purchasedate BETWEEN %s AND %s
    """, conn, params=(from_datetime, to_datetime))

    total_sales = float(sales['total_sales'][0]) if sales['total_sales'][0] else 0
    total_purchases = float(purchases['total_purchases'][0]) if purchases['total_purchases'][0] else 0
    net_profit = total_sales - total_purchases

    st.metric("💰 إجمالي المبيعات", f"{total_sales:.2f}")
    st.metric("📦 إجمالي المشتريات", f"{total_purchases:.2f}")
    st.metric("🏆 صافي الربح", f"{net_profit:.2f}")

    # أكثر المنتجات مبيعًا
    top_products = pd.read_sql("""
        SELECT p.productname, SUM(s.quantitysold) as total_qty
        FROM sales s
        JOIN products p ON s.productid = p.productid
        WHERE s.saledate BETWEEN %s AND %s
        GROUP BY p.productname
        ORDER BY total_qty DESC
        LIMIT 10
    """, conn, params=(from_datetime, to_datetime))
    st.write("📌 أكثر المنتجات مبيعًا")
    st.dataframe(top_products)

    # أكثر الفئات مبيعًا
    top_categories = pd.read_sql("""
        SELECT p.category, SUM(s.quantitysold) as total_qty
        FROM sales s
        JOIN products p ON s.productid = p.productid
        WHERE s.saledate BETWEEN %s AND %s
        GROUP BY p.category
        ORDER BY total_qty DESC
        LIMIT 10
    """, conn, params=(from_datetime, to_datetime))
    st.write("📌 أكثر الفئات مبيعًا")
    st.dataframe(top_categories)

    conn.close()
