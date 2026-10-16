-- Upserts the failures summary from the failures count view.
MERGE monitoring.job_failure_summary AS summary
USING monitoring.v_failures_count_by_feature AS failures
ON summary.featureName = failures.featureName
WHEN MATCHED THEN
  UPDATE SET
    failuresCount = summary.failuresCount + failures.failuresCount,
    lastFailureDate = GREATEST(summary.lastFailureDate, failures.lastFailureDate)
WHEN NOT MATCHED THEN
  INSERT (featureName, failuresCount, lastFailureDate)
  VALUES (failures.featureName, failures.failuresCount, failures.lastFailureDate)
