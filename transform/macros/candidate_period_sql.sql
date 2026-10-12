{% macro candidate_period_sql() %}
    {% set period = var('candidate_period', '') %}
    {% if period is not string or not modules.re.fullmatch('[0-9]{4}-(0[1-9]|1[0-2])-01', period) %}
        {{ exceptions.raise_compiler_error('candidate_period must be an explicit ISO month') }}
    {% endif %}
    {{ return("DATE '" ~ period ~ "'") }}
{% endmacro %}
