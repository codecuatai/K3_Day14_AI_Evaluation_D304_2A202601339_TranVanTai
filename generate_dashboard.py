"""
Interactive AI Evaluation & Benchmarking Dashboard Generator
Generates a modern, glassmorphic dark-mode HTML dashboard visualizing
RAGAS metrics, failure taxonomy, radar charts, and interactive Q&A inspectors.
"""

from __future__ import annotations

import json
from pathlib import Path


def generate_html_dashboard(
    results_path: Path = Path("artifacts/benchmark_results.json"),
    golden_path: Path = Path("golden_dataset.json"),
    output_path: Path = Path("artifacts/dashboard.html"),
) -> Path:
    results_data = json.loads(results_path.read_text(encoding="utf-8"))
    golden_data = json.loads(golden_path.read_text(encoding="utf-8"))

    summary = results_data.get("summary", {})
    results_list = results_data.get("results", [])

    # Embed HTML template
    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AI Evaluation & Benchmarking Dashboard — Northstar Student Services</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        :root {{
            --bg-dark: #0f172a;
            --card-bg: rgba(30, 41, 59, 0.7);
            --card-border: rgba(255, 255, 255, 0.1);
            --primary-glow: #6366f1;
            --accent-cyan: #06b6d4;
            --accent-emerald: #10b981;
            --accent-rose: #f43f5e;
            --accent-amber: #f59e0b;
            --text-main: #f8fafc;
            --text-muted: #94a3b8;
        }}

        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
            font-family: 'Outfit', sans-serif;
        }}

        body {{
            background-color: var(--bg-dark);
            background-image: 
                radial-gradient(at 0% 0%, rgba(99, 102, 241, 0.15) 0px, transparent 50%),
                radial-gradient(at 100% 100%, rgba(6, 182, 212, 0.15) 0px, transparent 50%);
            background-attachment: fixed;
            color: var(--text-main);
            min-height: 100vh;
            padding: 2rem;
        }}

        .header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 2rem;
            padding-bottom: 1rem;
            border-bottom: 1px solid var(--card-border);
        }}

        .header h1 {{
            font-size: 2rem;
            font-weight: 700;
            background: linear-gradient(135deg, #818cf8, #38bdf8);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }}

        .header p {{
            color: var(--text-muted);
            font-size: 0.95rem;
            margin-top: 0.25rem;
        }}

        .badge-live {{
            background: rgba(16, 185, 129, 0.15);
            border: 1px solid rgba(16, 185, 129, 0.4);
            color: #34d399;
            padding: 0.4rem 0.8rem;
            border-radius: 9999px;
            font-size: 0.85rem;
            font-weight: 500;
            display: inline-flex;
            align-items: center;
            gap: 0.5rem;
        }}

        .pulse-dot {{
            width: 8px;
            height: 8px;
            background-color: #34d399;
            border-radius: 50%;
            box-shadow: 0 0 10px #34d399;
            animation: pulse 2s infinite;
        }}

        @keyframes pulse {{
            0% {{ transform: scale(0.95); box-shadow: 0 0 0 0 rgba(52, 211, 153, 0.7); }}
            70% {{ transform: scale(1); box-shadow: 0 0 0 10px rgba(52, 211, 153, 0); }}
            100% {{ transform: scale(0.95); box-shadow: 0 0 0 0 rgba(52, 211, 153, 0); }}
        }}

        /* Metrics Grid */
        .metrics-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 1.25rem;
            margin-bottom: 2rem;
        }}

        .metric-card {{
            background: var(--card-bg);
            backdrop-filter: blur(12px);
            border: 1px solid var(--card-border);
            border-radius: 1rem;
            padding: 1.25rem;
            transition: transform 0.2s ease, border-color 0.2s ease;
        }}

        .metric-card:hover {{
            transform: translateY(-4px);
            border-color: rgba(99, 102, 241, 0.4);
        }}

        .metric-title {{
            font-size: 0.85rem;
            color: var(--text-muted);
            text-transform: uppercase;
            letter-spacing: 0.05em;
            margin-bottom: 0.5rem;
        }}

        .metric-value {{
            font-size: 2.2rem;
            font-weight: 700;
        }}

        .val-good {{ color: #34d399; }}
        .val-warning {{ color: #fbbf24; }}
        .val-critical {{ color: #f87171; }}

        .metric-sub {{
            font-size: 0.8rem;
            color: var(--text-muted);
            margin-top: 0.4rem;
        }}

        /* Charts Layout */
        .charts-container {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(350px, 1fr));
            gap: 1.5rem;
            margin-bottom: 2rem;
        }}

        .chart-card {{
            background: var(--card-bg);
            backdrop-filter: blur(12px);
            border: 1px solid var(--card-border);
            border-radius: 1rem;
            padding: 1.5rem;
        }}

        .chart-card h3 {{
            font-size: 1.1rem;
            font-weight: 600;
            margin-bottom: 1rem;
            color: #e2e8f0;
        }}

        /* Controls Section */
        .table-section {{
            background: var(--card-bg);
            backdrop-filter: blur(12px);
            border: 1px solid var(--card-border);
            border-radius: 1rem;
            padding: 1.5rem;
        }}

        .controls-bar {{
            display: flex;
            gap: 1rem;
            margin-bottom: 1.5rem;
            flex-wrap: wrap;
        }}

        .search-input, .filter-select {{
            background: rgba(15, 23, 42, 0.6);
            border: 1px solid var(--card-border);
            color: var(--text-main);
            padding: 0.6rem 1rem;
            border-radius: 0.5rem;
            font-size: 0.95rem;
            outline: none;
        }}

        .search-input {{ flex-grow: 1; }}

        .search-input:focus, .filter-select:focus {{
            border-color: var(--primary-glow);
            box-shadow: 0 0 0 2px rgba(99, 102, 241, 0.2);
        }}

        /* Table Styling */
        .results-table {{
            width: 100%;
            border-collapse: collapse;
            font-size: 0.9rem;
        }}

        .results-table th {{
            text-align: left;
            padding: 0.8rem 1rem;
            background: rgba(15, 23, 42, 0.4);
            color: var(--text-muted);
            font-weight: 600;
            border-bottom: 1px solid var(--card-border);
        }}

        .results-table td {{
            padding: 0.9rem 1rem;
            border-bottom: 1px solid rgba(255, 255, 255, 0.05);
        }}

        .results-table tr:hover {{
            background: rgba(255, 255, 255, 0.02);
        }}

        .badge-diff {{
            padding: 0.25rem 0.6rem;
            border-radius: 0.375rem;
            font-size: 0.75rem;
            font-weight: 600;
            text-transform: uppercase;
        }}

        .diff-easy {{ background: rgba(16, 185, 129, 0.15); color: #34d399; }}
        .diff-medium {{ background: rgba(59, 130, 246, 0.15); color: #60a5fa; }}
        .diff-hard {{ background: rgba(245, 158, 11, 0.15); color: #fbbf24; }}
        .diff-adversarial {{ background: rgba(244, 63, 94, 0.15); color: #fb7185; }}

        .status-pass {{ color: #34d399; font-weight: 600; }}
        .status-fail {{ color: #f87171; font-weight: 600; }}

        .mono-text {{
            font-family: 'JetBrains Mono', monospace;
            font-size: 0.85rem;
        }}
    </style>
</head>
<body>
    <div class="header">
        <div>
            <h1>AI Evaluation & Benchmarking Dashboard</h1>
            <p>Domain: Northstar University Student Services • AICB-P1 Phase 1 Evaluation Pipeline</p>
        </div>
        <div class="badge-live">
            <span class="pulse-dot"></span>
            Evaluation Pipeline Verified
        </div>
    </div>

    <!-- Top KPI Cards -->
    <div class="metrics-grid">
        <div class="metric-card">
            <div class="metric-title">Pass Rate</div>
            <div class="metric-value val-critical">{summary.get("pass_rate", 0.0) * 100:.1f}%</div>
            <div class="metric-sub">{summary.get("passed", 0)} / {summary.get("total", 0)} QAs Passed</div>
        </div>
        <div class="metric-card">
            <div class="metric-title">Context Recall</div>
            <div class="metric-value val-good">{summary.get("avg_context_recall", 0.0) * 100:.1f}%</div>
            <div class="metric-sub">Retriever Evidence Coverage</div>
        </div>
        <div class="metric-card">
            <div class="metric-title">Context Precision</div>
            <div class="metric-value val-good">{summary.get("avg_context_precision", 0.0) * 100:.1f}%</div>
            <div class="metric-sub">Rank-aware AP@K Quality</div>
        </div>
        <div class="metric-card">
            <div class="metric-title">Faithfulness</div>
            <div class="metric-value val-critical">{summary.get("avg_faithfulness", 0.0) * 100:.1f}%</div>
            <div class="metric-sub">Grounding in Context</div>
        </div>
        <div class="metric-card">
            <div class="metric-title">Answer Relevance</div>
            <div class="metric-value val-critical">{summary.get("avg_relevance", 0.0) * 100:.1f}%</div>
            <div class="metric-sub">Alignment to User Intent</div>
        </div>
    </div>

    <!-- Charts Row -->
    <div class="charts-container">
        <div class="chart-card">
            <h3>RAG Triad & Evaluation Radar</h3>
            <canvas id="radarChart"></canvas>
        </div>
        <div class="chart-card">
            <h3>Failure Taxonomy Distribution</h3>
            <canvas id="failureDoughnut"></canvas>
        </div>
    </div>

    <!-- Detailed Table -->
    <div class="table-section">
        <div class="controls-bar">
            <input type="text" id="searchInput" class="search-input" placeholder="Search by Question, ID, or Failure Type...">
            <select id="diffFilter" class="filter-select">
                <option value="ALL">All Difficulties</option>
                <option value="easy">Easy</option>
                <option value="medium">Medium</option>
                <option value="hard">Hard</option>
                <option value="adversarial">Adversarial</option>
            </select>
        </div>

        <table class="results-table">
            <thead>
                <tr>
                    <th>ID</th>
                    <th>Difficulty</th>
                    <th>Question</th>
                    <th>Recall</th>
                    <th>Precision</th>
                    <th>Faithfulness</th>
                    <th>Relevance</th>
                    <th>Completeness</th>
                    <th>Overall</th>
                    <th>Status</th>
                    <th>Failure Type</th>
                </tr>
            </thead>
            <tbody id="tableBody">
"""

    for r in results_list:
        diff_cls = f"diff-{r.get('difficulty', 'easy')}"
        status_cls = "status-pass" if r.get("passed") else "status-fail"
        status_txt = "PASS" if r.get("passed") else "FAIL"
        
        html_content += f"""
                <tr data-diff="{r.get('difficulty')}" data-text="{r.get('id')} {r.get('question')} {r.get('failure_type')}">
                    <td class="mono-text">{r.get('id')}</td>
                    <td><span class="badge-diff {diff_cls}">{r.get('difficulty')}</span></td>
                    <td>{r.get('question')}</td>
                    <td class="mono-text">{r.get('context_recall', 0.0):.2f}</td>
                    <td class="mono-text">{r.get('context_precision', 0.0):.2f}</td>
                    <td class="mono-text">{r.get('faithfulness', 0.0):.2f}</td>
                    <td class="mono-text">{r.get('relevance', 0.0):.2f}</td>
                    <td class="mono-text">{r.get('completeness', 0.0):.2f}</td>
                    <td class="mono-text" style="font-weight: 600;">{r.get('overall', 0.0):.3f}</td>
                    <td class="{status_cls}">{status_txt}</td>
                    <td class="mono-text" style="color: #cbd5e1;">{r.get('failure_type') or '—'}</td>
                </tr>
        """

    html_content += f"""
            </tbody>
        </table>
    </div>

    <script>
        // Radar Chart Initialization
        const ctxRadar = document.getElementById('radarChart').getContext('2d');
        new Chart(ctxRadar, {{
            type: 'radar',
            data: {{
                labels: ['Context Recall', 'Context Precision', 'Faithfulness', 'Relevance', 'Completeness'],
                datasets: [{{
                    label: 'Evaluation Baseline',
                    data: [
                        {summary.get("avg_context_recall", 0.0)},
                        {summary.get("avg_context_precision", 0.0)},
                        {summary.get("avg_faithfulness", 0.0)},
                        {summary.get("avg_relevance", 0.0)},
                        {summary.get("avg_completeness", 0.0)}
                    ],
                    backgroundColor: 'rgba(99, 102, 241, 0.25)',
                    borderColor: '#818cf8',
                    pointBackgroundColor: '#6366f1',
                    pointBorderColor: '#fff',
                    pointHoverBackgroundColor: '#fff',
                    pointHoverBorderColor: '#6366f1'
                }}]
            }},
            options: {{
                scales: {{
                    r: {{
                        angleLines: {{ color: 'rgba(255, 255, 255, 0.1)' }},
                        grid: {{ color: 'rgba(255, 255, 255, 0.1)' }},
                        pointLabels: {{ color: '#94a3b8', font: {{ family: 'Outfit', size: 12 }} }},
                        ticks: {{ color: '#64748b', backdropColor: 'transparent' }},
                        suggestedMin: 0,
                        suggestedMax: 1
                    }}
                }},
                plugins: {{
                    legend: {{ labels: {{ color: '#f8fafc' }} }}
                }}
            }}
        }});

        // Doughnut Chart Initialization
        const ctxDoughnut = document.getElementById('failureDoughnut').getContext('2d');
        new Chart(ctxDoughnut, {{
            type: 'doughnut',
            data: {{
                labels: ['Hallucination', 'Off-topic', 'Irrelevant', 'Incomplete'],
                datasets: [{{
                    data: [
                        {summary.get("failure_types", {}).get("hallucination", 0)},
                        {summary.get("failure_types", {}).get("off_topic", 0)},
                        {summary.get("failure_types", {}).get("irrelevant", 0)},
                        {summary.get("failure_types", {}).get("incomplete", 0)}
                    ],
                    backgroundColor: ['#f43f5e', '#f59e0b', '#06b6d4', '#8b5cf6'],
                    borderWidth: 0
                }}]
            }},
            options: {{
                plugins: {{
                    legend: {{ position: 'bottom', labels: {{ color: '#f8fafc', font: {{ family: 'Outfit' }} }} }}
                }},
                cutout: '70%'
            }}
        }});

        // Table Search & Filter Logic
        const searchInput = document.getElementById('searchInput');
        const diffFilter = document.getElementById('diffFilter');
        const rows = document.querySelectorAll('#tableBody tr');

        function filterTable() {{
            const searchTerm = searchInput.value.toLowerCase();
            const selectedDiff = diffFilter.value;

            rows.forEach(row => {{
                const text = row.getAttribute('data-text').toLowerCase();
                const diff = row.getAttribute('data-diff');
                const matchesSearch = text.includes(searchTerm);
                const matchesDiff = selectedDiff === 'ALL' || diff === selectedDiff;

                if (matchesSearch && matchesDiff) {{
                    row.style.display = '';
                }} else {{
                    row.style.display = 'none';
                }}
            }});
        }}

        searchInput.addEventListener('input', filterTable);
        diffFilter.addEventListener('change', filterTable);
    </script>
</body>
</html>
"""

    output_path.write_text(html_content, encoding="utf-8")
    return output_path


if __name__ == "__main__":
    out = generate_html_dashboard()
    print(f"[OK] Generated WOW Evaluation Dashboard: {out.resolve()}")

