# Privacy Boundaries

## Core rule

Group context and private BodyOS context remain separated.

## Group may contain

- shared expert knowledge
- public check-in
- public challenge
- explicitly shared completion result

## Private BodyOS may contain

- Apple Health derived metrics
- CGM
- HRV
- sleep
- InBody
- Meal Event
- Body Check
- experiment
- Personal Body Model

## Never commit real health evidence

Do not commit:

- real HealthKit exports
- real glucose series
- private PDFs
- names / identities
- tokens
- Feishu secrets
- OAuth credentials
- pairing artifacts
- private experiment evidence

Demo fixtures must be synthetic or explicitly de-identified.
