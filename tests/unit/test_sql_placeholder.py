from loom.tasks import generate_placeholder_sql_plan


def test_generate_placeholder_sql_plan_doris_context():
    template = (
        "产品分析最畅销产品为{{top_product: 销量最高的产品}}，"
        "累计销售{{sum: 该产品总销量}}件，贡献收入{{sum: 该产品总收入}}元"
    )

    plan = generate_placeholder_sql_plan(
        context_template=template,
        schedule="0 9 * * *",
        window_start="2025-10-21",
        window_end="2025-10-21",
        data_source={
            "type": "doris",
            "host": "192.168.31.160",
            "user": "root",
            "password": "",
            "database": "retail_db",
        },
    )

    assert plan.schedule == "0 9 * * *"
    assert plan.window_start == "2025-10-21"
    assert plan.window_end == "2025-10-21"
    assert plan.data_source["host"] == "192.168.31.160"
    assert plan.data_source["type"] == "doris"

    placeholders = plan.placeholder_columns
    assert placeholders["top_product:销量最高的产品"] == "top_product_name"
    assert placeholders["sum:该产品总销量"] == "total_quantity"
    assert placeholders["sum:该产品总收入"] == "total_revenue"

    sql = plan.sql
    assert sql.startswith("SELECT")
    assert "FROM retail_db.orders" in sql
    assert "DATE_ADD('2025-10-21', INTERVAL 1 DAY)" in sql
