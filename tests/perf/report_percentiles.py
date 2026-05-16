"""Печать перцентилей по сырым таймингам pytest-benchmark.

pytest-benchmark в табличном выводе показывает min / max / mean / stddev /
median / IQR, но не выводит 95-й и 99-й перцентили — а именно они нужны
для оценки хвостовых задержек, на которые ориентировано требование
по производительности. Этот скрипт читает JSON-отчёт прогона и считает
перцентили вручную из сырых таймингов каждой итерации.

Использование:
    cd tests
    pytest perf --benchmark-only --benchmark-json=perf_results.json
    python perf/report_percentiles.py perf_results.json

Или без аргумента — берётся ./perf_results.json по умолчанию.
"""
import argparse
import json
import sys
from pathlib import Path


def percentile(sorted_values, p):
    """p-й перцентиль методом «ближайшего ранга».

    Для небольших выборок (N < 100) это эквивалентно соглашению, принятому
    в большинстве инструментов нагрузочного тестирования (k6, Locust):
    rank = ceil(p/100 * N), индексация с единицы.
    """
    if not sorted_values:
        return float('nan')
    n = len(sorted_values)
    rank = max(1, int(round(p / 100 * n)))
    return sorted_values[rank - 1]


def collect_rows(report):
    rows = []
    for bench in report['benchmarks']:
        times = sorted(bench['stats']['data'])  # секунды
        rows.append({
            'name': bench['name'],
            'n': len(times),
            'median_ms': percentile(times, 50) * 1000,
            'p95_ms': percentile(times, 95) * 1000,
            'p99_ms': percentile(times, 99) * 1000,
            'max_ms': times[-1] * 1000,
        })
    rows.sort(key=lambda r: r['name'])
    return rows


def print_table(rows):
    header = f"{'name':<55} {'n':>5} {'median':>11} {'p95':>11} {'p99':>11} {'max':>11}"
    print(header)
    print('-' * len(header))
    for r in rows:
        print(
            f"{r['name']:<55} {r['n']:>5} "
            f"{r['median_ms']:>9.3f}ms "
            f"{r['p95_ms']:>9.3f}ms "
            f"{r['p99_ms']:>9.3f}ms "
            f"{r['max_ms']:>9.3f}ms"
        )


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        'json_path',
        nargs='?',
        default='perf_results.json',
        help='Путь к JSON-отчёту pytest-benchmark (по умолчанию: ./perf_results.json)',
    )
    args = parser.parse_args()

    path = Path(args.json_path)
    if not path.exists():
        sys.exit(
            f"Файл {path} не найден. Сначала запусти:\n"
            f"    pytest perf --benchmark-only --benchmark-json={path}"
        )

    with path.open() as f:
        report = json.load(f)

    rows = collect_rows(report)
    print_table(rows)


if __name__ == '__main__':
    main()
