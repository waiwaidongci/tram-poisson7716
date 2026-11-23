import csv
from src.config.settings import ARTIFACTS


def safe_cell(value):
    if isinstance(value, str) and (value.lstrip().startswith(('=', '+', '-', '@'))
                                   or value.startswith(('\t', '\r', '\n'))):
        return "'" + value
    return value


def write_report(run_id, attempt, result):
    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    name = f'analysis-{run_id}-{attempt}.csv'
    path = ARTIFACTS / name
    staging = path.with_suffix('.tmp')
    with staging.open('w', encoding='utf-8-sig', newline='') as output:
        writer = csv.writer(output)
        writer.writerow([safe_cell(result['headline'])])
        writer.writerow([safe_cell(result.get('note', ''))])
        for metric in result['metrics']:
            writer.writerow([safe_cell(metric['label']), safe_cell(metric['value']), safe_cell(metric.get('detail', ''))])
        for table in result['tables']:
            writer.writerow([])
            writer.writerow([safe_cell(table['title'])])
            columns = table['columns']
            writer.writerow([safe_cell(column['label']) for column in columns])
            writer.writerows([safe_cell(row.get(column['key'])) for column in columns] for row in table['rows'])
    staging.replace(path)
    return name
