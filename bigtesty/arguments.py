import argparse

parser = argparse.ArgumentParser()
parser.add_argument('--root_folder', dest='root_folder', type=str, help='Root folder')
parser.add_argument('--project_id', dest='project_id', type=str, help='GCP Project ID')
parser.add_argument('--datasets_hash', dest='datasets_hash', type=str, help='Unique hash to isolate datasets')
args = parser.parse_args()
