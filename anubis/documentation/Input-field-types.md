# Input field types

The input fields are the means to store information in proposals, reviews, decisions and grants. They have types which define what kind of information they
can store.

## Available input field types

- **Line**: One single line of text, such as a name or title.
  May contain any text.
- **Email**: One single email address, which must look like a proper email
  address. However, its actual validity is not checked.
- **Boolean**: A Yes/No question.
- **Select**: Choose among a set of given options defined on setup.
- **Integer**: A number that is a whole integer.
- **Float**: A number that may contain fractions.
- **Score**: A number in the range if integer values defined on setup.
- **Rank**: A number in the series 1, 2, 3,...
- **Text**: A multiline text which may use Markdown formatting.
- **Document**: An attached file.

## Common options for all input field types

All input field types have a number of options that can be set at creation
or modified later. These are:

## Rank

A field of type rank is intended for reviews. The reviewer must assign
a value to the field of each of her reviews in a call such that the
values are unique and consecutive starting from 1, else an error will
be flagged.

A field set as banner will produce an extra column named "Ranking
factor" (F(x) below) which is computed from all values in finalized
reviews in that call. The formula is:

```
    A(i) = total number of ranked proposals for reviewer i
    R(x,i) = rank for proposal x by reviewer i

    F(x) = round(decimals(1, 10 * average(all reviewers( (A(i) - R(x, i) + 1) / A(i)) ))))
```

For a proposal which has been ranked 1 by all reviewers of it, this will produce
a ranking factor of 10, which is the maximum. If a reviewer has ranked it at,
say, 3, then the ranking factor will become slightly less than 10.
