# URL Shortener Project

**Live API:** https://53udtgf0zh.execute-api.eu-central-1.amazonaws.com/

📖 Want the full, beginner-friendly walkthrough of every step, command,
and decision made in this project? See
[PROJECT_GUIDE.md](./PROJECT_GUIDE.md).

## What is this project, in one sentence?

A serverless URL shortener: POST a long URL and get back a short code;
visit that code and get redirected to the original — built with Lambda,
API Gateway, and DynamoDB, deployed through Terraform + CI/CD.

## Why this project exists

The sixth project in this series, chosen to fill the last major gap in
the portfolio: **data persistence**. Every previous serverless project
either returned fixed/generated data (the quote API) or had no data
layer at all. This one introduces DynamoDB — AWS's managed, serverless
NoSQL database — and demonstrates a genuine CRUD-style pattern (write
one item, read it back by key) plus HTTP redirects, a new response type
not used in any earlier project.

## How it works

```
POST /shorten {"url": "https://example.com/very/long/url"}
      -> Lambda generates a random short code
      -> writes {id: code, original_url: url} to DynamoDB
      -> returns {"short_code": "...", "original_url": "..."}

GET /{code}
      -> Lambda looks up the code in DynamoDB
      -> returns a 302 redirect to the original URL
```

## Architecture

- **DynamoDB** — a single table (`id` as the primary key), billed
  `PAY_PER_REQUEST` (pay only for actual reads/writes, no fixed
  capacity to provision or pay for when idle).
- **Lambda** — one function handling both routes, branching on the HTTP
  method (`POST` vs `GET`).
- **API Gateway** — two routes: `POST /shorten` and `GET /{code}` (a
  path parameter matching any single path segment).
- **IAM** — the Lambda's execution role has a custom **inline** policy
  (not an AWS-managed one) granting exactly `GetItem`/`PutItem` on this
  one specific table — nothing broader.

## Problems & fixes — quick reference

| Problem | Why it happened | How it was fixed |
|---|---|---|
| None — this project's pipeline succeeded on the first real deploy attempt | Applying lessons from every earlier project (checking which AWS services the Terraform code actually touches before picking IAM policies, formatting discipline, generating long files instead of risky terminal pastes) | N/A — a good sign the earlier projects' lessons had actually been internalized |
| Local PC lost the `terraform-modules` project folder during an unrelated backup/restore | The backup process dropped a folder that hadn't been re-synced | Verified using `git status` + `git fetch` across every repo that nothing was actually lost (GitHub had everything), then re-cloned it |

## Cost notes

Like the Lambda quote API, this project is genuinely low-cost to leave
deployed indefinitely: Lambda and API Gateway bill per request (near
zero at portfolio-demo traffic levels), and DynamoDB's `PAY_PER_REQUEST`
mode means no idle capacity cost either. No `destroy.yml` workflow was
needed for this reason.

## How to reproduce this project

1. Install Git and Terraform.
2. Create a GitHub repo, clone it locally.
3. Write a Lambda function using `boto3` (pre-installed in the Lambda
   Python runtime — no `requirements.txt` needed) to read/write
   DynamoDB, branching on `event["requestContext"]["http"]["method"]`.
4. Write Terraform: a DynamoDB table, a Lambda function (with the table
   name passed in as an environment variable), an IAM role with an
   inline policy scoped to that one table, and an API Gateway with a
   `POST` route and a `GET /{code}` path-parameter route.
5. Create a dedicated IAM user with managed policies for Lambda/API
   Gateway/DynamoDB, plus a scoped custom policy for IAM role and
   inline-policy management.
6. Store the keys as GitHub Secrets, set up a protected `production`
   environment with required reviewers.
7. Push, approve, and test with `curl -X POST .../shorten` followed by
   `curl -i .../<code>` to see the redirect.

## What's next (possible future additions)

- [ ] Add a "click count" attribute, incremented on every redirect.
- [ ] Add expiration (TTL) so old short codes automatically clean
      themselves up.
- [ ] Validate that submitted URLs are actually well-formed before
      storing them.
