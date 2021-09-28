# Input field types

The input fields are the means to store information in proposals, reviews, decisions and grants. They have types which define what kind of information they
can store.

## Available input field types

- **Line**. One single line of text, such as a name or title.
- **Email**. One single email address.
- **Boolean**. A selection between Yes and No.
- **Select**. A choice among a set of text given values.
- **Integer**. A number that is a whole integer.
- **Float**. A number that may contain fractions.
- **Score**. A number in the range of integer values defined on setup.
- **Rank**. A number in the series 1, 2, 3,...
- **Text**. A multiline text which may use Markdown formatting.
- **Document**. An attached file.

## Common settings for all input field types

All input field types have a number of settings that can be set at creation
or modified later. These are:

- **Identifier**. The internal name of the field, which must be unique within
  the form. It must begin with a letter and continue with letters,
  numbers or underscores.

- **Title**. The name of the field as shown to the user.
  Defaults to the identifier capitalized.

- **Required**. Is a value required in this field for the form to be valid?

- **Staff edit**. Only the staff may edit the field. The user will see it.

- **Staff only**. Only the staff may edit and view the field.
  It is not visible to the user.

- **Banner**. The field will be shown in various tables.

- **Description**. The help text displayed for the field.
   May contain Markdown formatting.

## Line field

One single line of text, such as a name or title. May contain any text.

- **Maxlength**. The maximum number of characters allowed in the
  field, blanks included.

## Email field

One single email address, which must look like a proper email
address. However, its actual validity is not checked.

## Boolean field

A selection between Yes and No. If it is not required, then also "No
value" will be allowed.

## Select field

A choice among a set of given text values.

- **Selection values**.  The values to let the user choose from. Give
  the values as text where each line is one value.

- **Multiple choice**. Is the user allowed to choose more than one value?

## Integer field

A number that is a whole integer.

- **Minimum**: An optional lower limit for the value given by the user.

- **Maximum**: An optional upper limit for the value given by the user.

## Float field

A number that may contain fractions, i.e. a decimal point.

- **Minimum**: An optional lower limit for the value given by the user.

- **Maximum**: An optional upper limit for the value given by the user.

## Score field

A number in the range of integer values defined on setup. The choice
of value is presented as a set of buttons, or optionally by input from
a slider.

- **Minimum**: The lower limit for the value given by the user.

- **Maximum**: The upper limit for the value given by the user.

## Rank field

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

**NOTE**: This is currently implemented only for reviews; it is not
very meaningful for other entities.

## Text field

A multiline text which may use Markdown formatting.

- **Maxlength**. The maximum number of characters allowed in the
  field, blanks included.

## Document field

 An attached file.

- **Extensions**. A list of allowed extensions for the attached file.
  A simple-minded mechanism to restrict the allowed types of files.

## Repeat field

This fiel solves the problem when the number of input fields depends
on a number that the user must input. If the user has e.g. three
collaborators, the user should then add the name, affiliation and
email address in three copies.

When the user inputs a number in a repeat field, the system brings up
that number of copies of the other fields that have been associated
with.

After having defined a repeat field, the other fields that should be
repeated need be associated with it. When creating a new field, there
will be a select list field to specify whether that field is repeated
by a previously defined repeat field.

**NOTE**: This is currently implemented only for grants.
