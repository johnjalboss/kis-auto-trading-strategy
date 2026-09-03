from chart_generator import generate_pnl_chart
path, text = generate_pnl_chart(days=30)
print("CHART_PATH:", path)
print("CHART_TEXT:\n", text)
