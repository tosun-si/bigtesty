{% from "macros.sql" import partition_filter %}
-- Production job, run every day: the ds and env vars are rendered by monitoring.templating, the feature_names and
-- min_failures query parameters are passed by the job.
DELETE FROM `my-prod-project.monitoring.daily_failures` WHERE day = '{{ ds }}';

INSERT INTO `my-prod-project.monitoring.daily_failures` (day, featureName, failuresCount, env)
SELECT
  DATE(dwhCreationDate) AS day,
  featureName,
  COUNT(*) AS failuresCount,
  '{{ env }}' AS env
FROM `my-prod-project.monitoring.job_failure`
WHERE {{ partition_filter('dwhCreationDate', ds) }}
  AND featureName IN UNNEST(@feature_names)
GROUP BY day, featureName
HAVING COUNT(*) >= @min_failures;
