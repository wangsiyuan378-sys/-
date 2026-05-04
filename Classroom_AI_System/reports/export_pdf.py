from fpdf import FPDF
import sqlite3
import pandas as pd
import os


def export_to_pdf(db_path="data/classroom.db", output_folder="reports"):
    # 确保文件夹存在
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    output_path = os.path.join(output_folder, "Classroom_Report.pdf")

    # 1. 从数据库提取汇总数据
    conn = sqlite3.connect(db_path)
    df = pd.read_sql_query("SELECT score, status FROM focus_log", conn)
    conn.close()

    if df.empty:
        return False, "数据库为空，无法生成报告"

    # 2. 计算简单统计量
    avg_score = df['score'].mean()
    focus_rate = (df['status'] == '专注').sum() / len(df) * 100

    # 3. 编写 PDF
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(200, 10, txt="Classroom Effectiveness Report", ln=True, align='C')

    pdf.set_font("Arial", size=12)
    pdf.ln(10)
    pdf.cell(200, 10, txt=f"Average Focus Score: {avg_score:.2f}", ln=True)
    pdf.cell(200, 10, txt=f"Concentration Rate: {focus_rate:.2f}%", ln=True)
    pdf.cell(200, 10, txt=f"Total Records: {len(df)}", ln=True)

    pdf.output(output_path)
    return True, output_path