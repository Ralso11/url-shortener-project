# The Complete Guide to This Project
### (Written so anyone, even with zero background, can understand it)

This is the sixth project in a small portfolio series. It assumes the
basics from the first project's guide (Git, GitHub, Terraform, CI/CD)
and the second project's guide (Lambda, API Gateway) are already
familiar. This one is entirely about **persistent data** — storing and
retrieving information, rather than just computing a response on the
fly.

---

## Part 1 — Why this project matters: the missing piece

Every previous serverless project in this series either had no data to
remember (the quote API picked from a fixed list) or had nowhere to
persist anything at all. Almost every real-world API eventually needs
to actually **store** something — user accounts, orders, messages,
in this case, URL mappings. This project introduces that missing piece:
**DynamoDB**, AWS's managed, serverless database.

## Part 2 — What is DynamoDB, in plain terms?

Think of a traditional database like a filing cabinet with labeled
folders (tables), each folder containing index cards (rows) with fixed
columns. DynamoDB is looser: it's still organized into tables, but each
"item" (its word for a row) can have different fields — flexible, not
rigid. In exchange for that flexibility, DynamoDB is extremely fast at
one specific thing: looking up an item by its **primary key** — exactly
what this project needs (look up a short code, get back the URL).

**Why DynamoDB instead of a traditional SQL database here?** It's
**serverless**, matching the philosophy of the rest of this project —
no database server to provision, patch, or leave running. You're billed
per actual read/write (`PAY_PER_REQUEST` mode), not for idle capacity.

## Part 3 — The two operations, and how the Lambda code handles them

Both `POST /shorten` and `GET /{code}` are handled by the **same**
Lambda function — the code branches based on which HTTP method was
used:

```python
def handler(event, context):
    method = event["requestContext"]["http"]["method"]
    if method == "POST":
        return shorten_url(event)
    if method == "GET":
        return redirect_to_url(event)
```

### Shortening a URL (write)
```python
short_code = generate_short_code()
table.put_item(Item={
    "id": short_code,
    "original_url": original_url
})
```
`generate_short_code()` uses Python's `secrets` module (not the plain
`random` module — `secrets` is designed to be harder to predict, a
better default habit even for a small demo like this) to pick 6 random
letters/digits. `table.put_item(...)` writes a new item: the short code
becomes the primary key, paired with the original URL.

### Looking up a URL (read)
```python
short_code = event["pathParameters"]["code"]
response = table.get_item(Key={"id": short_code})
item = response.get("Item")
```
`event["pathParameters"]["code"]` is how API Gateway hands your code
the value that matched the `{code}` part of the URL path. `get_item`
looks up exactly one item by its key — fast, direct, no searching
through the whole table.

### The redirect itself
```python
return {
    "statusCode": 302,
    "headers": {"Location": item["original_url"]}
}
```
This is a genuinely new concept for this portfolio: instead of
returning JSON data for something to *read*, this tells the browser
"go somewhere else instead." `302` is the standard HTTP status code
for a temporary redirect; the `Location` header tells the browser
exactly where to go. Browsers automatically follow this — nothing
special needs to happen on the client side.

## Part 4 — The Terraform: connecting the pieces

**The table:**
```hcl
resource "aws_dynamodb_table" "urls" {
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "id"
  attribute {
    name = "id"
    type = "S"
  }
}
```
`hash_key = "id"` declares the primary key's name; the separate
`attribute` block declares its type (`S` = String). DynamoDB only
requires you to declare the *key* attribute's type up front — unlike a
SQL table, you don't have to predefine every possible field an item
might have.

**Passing the table name to the Lambda function:**
```hcl
resource "aws_lambda_function" "shortener" {
  environment {
    variables = {
      TABLE_NAME = aws_dynamodb_table.urls.name
    }
  }
}
```
This is how `os.environ["TABLE_NAME"]` in the Python code gets its
value — Terraform passes it in at deploy time, rather than it being
hardcoded in the application code.

**Scoped, inline database access:**
```hcl
resource "aws_iam_role_policy" "dynamodb_access" {
  role = aws_iam_role.lambda_exec.id
  policy = jsonencode({
    Statement = [{
      Action   = ["dynamodb:GetItem", "dynamodb:PutItem"]
      Resource = aws_dynamodb_table.urls.arn
    }]
  })
}
```
Notice this is `aws_iam_role_policy` (singular, inline), not
`aws_iam_role_policy_attachment` like in earlier projects.
`_attachment` connects an *existing*, separately-defined policy (often
an AWS-managed one) to a role. A plain `aws_iam_role_policy` instead
**creates a brand-new, one-off policy directly inside this file**,
scoped to exactly what's needed — appropriate here because no
AWS-managed policy exists for "access to this one specific table";
that has to be custom by nature.

**The path-parameter route:**
```hcl
resource "aws_apigatewayv2_route" "redirect" {
  route_key = "GET /{code}"
}
```
The curly braces mark `{code}` as a variable segment of the URL —
`GET /aZ3x9K`, `GET /xyz123`, anything matches, and whatever was
actually in that position becomes available in the Lambda's `event` as
`pathParameters.code`.

## Part 5 — Why this one deployed cleanly on the first try

Unlike several earlier projects in this series, this one's pipeline
succeeded on the very first real deploy attempt — no missing IAM
permissions, no formatting failures. That's not luck; it reflects
lessons carried forward from every previous project: checking which
distinct AWS services the Terraform code actually touches before
picking IAM policies (Lambda, API Gateway, DynamoDB, and IAM role
management — all four were covered from the start this time), keeping
formatting consistent, and using the safer file-download method instead
of risky long terminal pastes for anything substantial.

## Part 6 — A non-technical lesson: verifying before panicking

Partway through this project, a routine check revealed that the
`terraform-modules` project folder had gone missing from the local PC
— traced back to an unrelated backup/restore process. Rather than
assuming work was lost, a systematic check (`git status` and
`git fetch` across every repo) confirmed that GitHub already had
everything safely — only the local folder was missing, easily fixed
with a fresh `git clone`. This is a genuinely useful habit: verify
precisely what's actually wrong before assuming the worst, especially
when a tool like Git exists specifically to make that verification easy.

## Part 7 — Command/concept glossary (new items vs previous projects)

| Term | Plain-language meaning |
|---|---|
| DynamoDB | AWS's managed, serverless NoSQL database |
| Item (DynamoDB) | The equivalent of a "row" — one entry in a table |
| Primary key / hash key | The field DynamoDB uses to uniquely identify and quickly look up each item |
| `PAY_PER_REQUEST` | A DynamoDB billing mode charging per actual read/write, not for reserved idle capacity |
| `boto3` | AWS's official Python library for talking to AWS services from code |
| Path parameter (`{code}`) | A variable segment of a URL route, captured and made available to the handling code |
| HTTP redirect (302) | A response telling the client "go here instead," rather than returning data directly |
| Inline IAM policy | A custom, one-off policy defined directly for a role, as opposed to attaching a separately-defined (often AWS-managed) one |

## Part 8 — How to explain this project in an interview

> "I built a serverless URL shortener using Lambda, API Gateway, and
> DynamoDB — the first project in my portfolio with actual data
> persistence. One Lambda function handles both writing new short-code
> mappings and reading them back for redirects, branching on the HTTP
> method. I scoped the Lambda's database access with a custom inline
> IAM policy limited to exactly the two operations it needs on that one
> specific table, rather than a broader managed policy. Because I'd
> already hit and fixed IAM permission gaps in earlier projects, I made
> sure to account for every AWS service my Terraform code touched up
> front, and this one deployed successfully on the very first attempt."

That story shows genuine progression across a portfolio — not just
"I can build things," but "I learn from what went wrong and apply it
forward."

---

*This document, together with the repo's README.md, covers everything
needed to fully understand, explain, and rebuild this project.*
