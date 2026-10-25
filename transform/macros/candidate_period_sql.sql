{% macro candidate_period_sql() %}
    {% set period = var('candidate_period', '') %}
    {% if period is not string or not modules.re.fullmatch('[0-9]{4}-(0[1-9]|1[0-2])-01', period) %}
        {{ exceptions.raise_compiler_error('candidate_period must be an explicit ISO month') }}
    {% endif %}
    {{ return("DATE '" ~ period ~ "'") }}
{% endmacro %}

{% macro candidate_start_period_sql() %}
    {% set start = var('candidate_start_period', var('candidate_period', '')) %}
    {% set end = var('candidate_period', '') %}
    {% if start is not string or not modules.re.fullmatch('[0-9]{4}-(0[1-9]|1[0-2])-01', start) or start > end %}
        {{ exceptions.raise_compiler_error('candidate_start_period must be an explicit ISO month <= candidate_period') }}
    {% endif %}
    {{ return("DATE '" ~ start ~ "'") }}
{% endmacro %}
