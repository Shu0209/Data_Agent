from data_agent.agents.graph import ai_data_agent


png_data = ai_data_agent.get_graph().draw_mermaid_png()

with open("data_agent_graph.png", "wb") as f:
    f.write(png_data)