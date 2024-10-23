import random
import datetime

# 扩展购买方信息
buyers = [
    {"name": "北京用友数能科技有限公司", "tax_id": "9111010834431437XQ"},
    {"name": "上海某某信息技术有限公司", "tax_id": "913101087982578XQ"},
    {"name": "广州某某电子科技有限公司", "tax_id": "914401083453445XQ"},
    {"name": "杭州科技发展有限公司", "tax_id": "915101087892345XQ"},
    {"name": "成都高新技术有限公司", "tax_id": "916601081292567XQ"}
]

# 扩展销售方信息
sellers = [
    {"name": "昆明盘智易联科技有限公司天津分公司", "tax_id": "91120112MA06K5P98J"},
    {"name": "某某软件有限公司", "tax_id": "9111010852741437XQ"},
    {"name": "重庆某某有限公司", "tax_id": "9115010852789637XP"},
    {"name": "深圳某某网络技术有限公司", "tax_id": "912301084356784XQ"}
]

# 扩展项目明细
services = [
    {"name": "运输服务客运服务费", "unit_price": 69.51, "tax_rate": 0.03},
    {"name": "物流服务费", "unit_price": 120.00, "tax_rate": 0.06},
    {"name": "技术服务费", "unit_price": 200.00, "tax_rate": 0.03},
    {"name": "软件开发服务费", "unit_price": 300.00, "tax_rate": 0.06},
    {"name": "咨询服务费", "unit_price": 500.00, "tax_rate": 0.06},
    {"name": "项目管理费", "unit_price": 800.00, "tax_rate": 0.03},
    {"name": "设备维护费", "unit_price": 1000.00, "tax_rate": 0.06}
]

# 随机生成发票号
def generate_invoice_number():
    return f"{random.randint(2412000000000000, 2412999999999999)}"

# 随机生成开票日期
def generate_invoice_date():
    today = datetime.date.today()
    return today.strftime("%Y年%m月%d日")

# 随机选择购买方信息
def generate_buyer_info():
    return random.choice(buyers)

# 随机选择销售方信息
def generate_seller_info():
    return random.choice(sellers)

# 随机生成项目明细
def generate_service_details():
    num_services = random.randint(2, 5)  # 每张发票随机选择 2 到 5 项服务
    service_details = []
    total_amount = 0
    total_tax = 0

    for _ in range(num_services):
        service = random.choice(services)
        quantity = random.randint(1, 10)
        service_total = service["unit_price"] * quantity
        tax_amount = service_total * service["tax_rate"]
        service_details.append({
            "name": service["name"],
            "quantity": quantity,
            "unit_price": service["unit_price"],
            "service_total": round(service_total, 2),
            "tax_rate": int(service["tax_rate"] * 100),
            "tax_amount": round(tax_amount, 2)
        })
        total_amount += service_total
        total_tax += tax_amount

    return service_details, round(total_amount, 2), round(total_tax, 2)

# 生成发票文本
def generate_invoice():
    invoice_number = generate_invoice_number()
    invoice_date = generate_invoice_date()
    buyer_info = generate_buyer_info()
    seller_info = generate_seller_info()
    services, subtotal, total_tax = generate_service_details()
    total_with_tax = round(subtotal + total_tax, 2)

    # 模拟开票人
    issuer = random.choice(["刘慧敏", "张三", "李四", "赵六", "王五"])

    # 生成发票文本
    invoice_text = (
        f"发票号: {invoice_number}\n"
        f"开票日期: {invoice_date}\n"
        f"购买方名称: {buyer_info['name']}\n"
        f"纳税人识别号: {buyer_info['tax_id']}\n"
        f"销售方名称: {seller_info['name']}\n"
        f"纳税人识别号: {seller_info['tax_id']}\n"
        "----------------------------------------\n"
        "项目明细:\n"
    )

    for service in services:
        invoice_text += (
            f"项目名称: {service['name']}\n"
            f"单价: ¥{service['unit_price']:.2f}\n"
            f"数量: {service['quantity']}\n"
            f"金额: ¥{service['service_total']:.2f}\n"
            f"税率: {service['tax_rate']}%\n"
            f"税额: ¥{service['tax_amount']:.2f}\n"
            "----------------------------------------\n"
        )

    invoice_text += (
        f"金额合计: ¥{subtotal:.2f}\n"
        f"税额合计: ¥{total_tax:.2f}\n"
        f"价税合计（大写）: ￥{total_with_tax}\n"
        f"开票人: {issuer}\n"
    )

    return invoice_text

# 将发票写入文件
def generate_invoices_to_file(filename, count):
    with open(filename, 'w', encoding='utf-8') as f:
        for _ in range(count):
            invoice = generate_invoice()
            f.write(invoice)
            f.write("\n" + "=" * 40 + "\n")  # 分隔符，用于区分每张发票

# 生成并写入10000张发票到文件
if __name__ == "__main__":
    output_filename = "generated_invoices.txt"
    generate_invoices_to_file(output_filename, 10)
    print(f"已生成 10 张发票，并保存到文件: {output_filename}")
