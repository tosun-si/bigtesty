from datasets_with_tables import datasets_with_tables, get_dataset, get_table_with_partitioning, \
    get_table

for dataset in datasets_with_tables:
    bq_dataset = get_dataset(dataset)

    for table in dataset["tables"]:
        bq_table = (
            get_table_with_partitioning(bq_dataset, table) if table.get("partitionType") is not None
            else get_table(bq_dataset, table)
        )
