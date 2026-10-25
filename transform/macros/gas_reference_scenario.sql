{% macro gas_reference_energy_basis_id() %}
    {{ return('EIA_US_AVERAGE_1036_BTU_PER_CUBIC_FOOT_SCENARIO_V1') }}
{% endmacro %}

{% macro gas_reference_mmbtu_per_m3() %}
    {# Fixed US-average scenario, never measured Vaca Muerta heating value. #}
    {% if var('gas_reference_btu_per_cubic_foot', 1036) != 1036
       or var('gas_reference_m3_per_cubic_foot', 0.028316846592) != 0.028316846592 %}
        {{ exceptions.raise_compiler_error('Changing the gas scenario constants requires a new versioned energy_basis contract') }}
    {% endif %}
    {{ return('(cast(1036 as float64) / cast(0.028316846592 as float64) / cast(1000000 as float64))') }}
{% endmacro %}
