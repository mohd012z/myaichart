import csv

def import_evidence_csv(path):
    with open(path,newline='',encoding='utf-8') as fh:
        return list(csv.DictReader(fh))
