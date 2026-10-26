# How to test Example App's issue sync

This is a fictional tone example, not a runbook for a real product. Replace every placeholder with verified project behavior before publishing. A confident lie with a numbered list is still a lie, you clipboard goblin.

## Assumptions, because optimism is not a test environment

- You have read the project's actual setup instructions.
- The app and its worker are running in a disposable test environment.
- You can sign in with a test account.
- You control a test repository that can receive throwaway issues.
- You know the actual app URL and webhook endpoint. Guessing a route does not summon it into existence.

## 1. Connect the test repository

1. Open `<verified integration settings page>`.
2. Choose `<actual connect action>`.
3. Authorize the test account and select the disposable repository.
4. Return to the app and confirm the repository is listed as connected.

Expected result:

- The app shows the intended repository, not your production incident tracker.
- The integration's verified status endpoint or connection record confirms the same account/repository.

If authorization returns you to a login screen, inspect the callback response and session handling. Do not mash Connect until OAuth gets tired and lets you in.

## 2. Test both directions, you ambitious half-tester

1. Create a uniquely named issue in the app.
2. Confirm it appears in the connected repository.
3. Edit its title in the repository.
4. Confirm the supported update appears back in the app.
5. Check the documented delivery log or worker state for that exact test event.

Expected result:

- One linked issue, not six increasingly desperate duplicates.
- The fields promised by the integration match in both systems.
- The delivery is recorded as completed, not merely accepted into a queue.

Do not claim comments, deletion or status mapping work unless you tested those supported behaviors separately. One successful title change is not a papal blessing for the entire integration.

## Common traps, lovingly arranged around the hole you fell into

- **Nothing arrives:** check the actual webhook delivery, response status and worker log in that order.
- **The endpoint returns success but nothing changes:** confirm processing completed. A queue receipt is not the final result.
- **Duplicates:** inspect retries and idempotency before clicking the button twelve more times.
- **Wrong repository:** verify the saved selection and account. The software cannot read the repository you meant emotionally.

## Final pass

- [ ] Correct test account and repository.
- [ ] Creation and supported updates verified in both directions.
- [ ] Matching external delivery and local processing evidence.
- [ ] No duplicate records or exposed credentials.
- [ ] Disposable test data cleaned up only with the appropriate permission.

Congratulations. You have tested the integration instead of briefly making eye contact with it.
