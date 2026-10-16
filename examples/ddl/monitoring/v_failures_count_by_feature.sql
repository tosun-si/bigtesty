CREATE VIEW monitoring.v_failures_count_by_feature AS
SELECT
  featureName,
  COUNT(*) AS failuresCount,
  MAX(dwhCreationDate) AS lastFailureDate
FROM monitoring.job_failure
GROUP BY featureName
