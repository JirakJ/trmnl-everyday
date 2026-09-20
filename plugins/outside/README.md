# Outside Window / Kdy ven?

![Synthetic demo](../../docs/previews/outside.png)

Rank up to three non-overlapping daylight windows over the next 72 hours. Presets
cover walking, running and cycling. All thresholds and the activity duration are
configurable. Every forecast hour touched by an activity must satisfy the limits;
missing data never counts as good weather. Suggestions are forecasts, not safety advice.

Use the [root installation guide](../../README.md). Copy `config.example.json`
to `private/outside.json`, change city and coordinates, and run:

```sh
.venv/bin/python -m everyday outside --config private/outside.json --push
```

Remove both coordinates to resolve a city by name. Ambiguous results are rejected;
set coordinates to select the exact city. `country_code` narrows geocoding results.
`timezone` controls displayed times. Temperature is Celsius and wind is km/h.
An empty result means no forecast window satisfies your preferences.

Data: [Open-Meteo](https://open-meteo.com/en/docs), locations: GeoNames via Open-Meteo.
The source credit is displayed on the screen. The free Open-Meteo hosted API is for
non-commercial use; commercial use needs a suitable plan. For a paid endpoint, set
`weather_api_key_env` to the name of an environment variable holding your API key
and configure coordinates explicitly to avoid the free geocoding endpoint.
See [provider terms](https://open-meteo.com/en/pricing). Open-source distribution
does not automatically make every deployment non-commercial.

Validation: synthetic rain-in-the-middle and missing-hour cases are covered by
`tests/test_outside.py`. Device/account delivery still requires your webhook URL.
