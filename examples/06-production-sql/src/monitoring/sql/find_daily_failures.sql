-- Production query of a dashboard: the failures of one feature since a day.
SELECT day, featureName, failuresCount
FROM `my-prod-project.monitoring.daily_failures`
WHERE featureName = @feature_name
  AND day >= @since
