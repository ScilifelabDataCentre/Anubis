# Privileges

 Anonymous users (not logged-in) are allowed to view open calls and not much else.

In order to create and edit anything in Anubis, a user account is required.

The privileges determine which actions are allowed for a logged-in user. The role of the user account controls this. A user account has one single role for
the whole system at all times. There are three roles:

1. **Admin**: The system administrator, who can do everything that can be done via the web interface.
2. **Staff**: The Anubis staff, who can view everything, but not change all that much.
3. **User**: Anyone who has registered an account in Anubis. She is allowed to create, edit and submit a proposal in an open call. She can view all her current and previous proposals, and view decisions and grant pages, if any, for each specific proposal.

Accounts with the user role can be given additional privileges, which relate
to specific calls only:

- A user can be set as a reviewer in a call, in which case she gets more
privileges for that call.
- In addition, a reviewer can be set as chair for that review. This gives
  further privileges.
- A user can be allowed to create calls, in which case she has more privileges
for that call.

Here's a summary of privileges for some actions. Note that some exceptions are omitted, such as a user explicitly allowing another user to view and/or edit their proposal.

<table class="table">

<tr>
<th></th>
<th>User</th>
<th>User (reviewer)</th>
<th>User (call creator)</th>
<th>Staff</th>
<th>Admin</th>
</tr>

<tr>
<th>Create proposal in open call</th>
<td><span class="bi-check-lg text-success"></span></td>
<td>N/A</td>
<td>N/A</td>
<td><span class="bi-check-lg text-success"></span></td>
<td><span class="bi-check-lg text-success"></span></td>
</tr>

<tr>
<th>Edit a proposal in open call</th>
<td><span class="bi-check-lg text-warning"></span> One's own</td>
<td><span class="bi-x-lg text-danger"></span></td>
<td><span class="bi-check-lg text-warning"></span> Any in call</td>
<td><span class="bi-check-lg text-success"></span></td>
<td><span class="bi-check-lg text-success"></span></td>
</tr>

<tr>
<th>View a proposal</th>
<td><span class="bi-check-lg text-warning"></span> One's own</td>
<td><span class="bi-check-lg text-warning"></span> Any in call</td>
<td><span class="bi-check-lg text-warning"></span> Any in call</td>
<td><span class="bi-check-lg text-success"></span></td>
<td><span class="bi-check-lg text-success"></span></td>
</tr>

<tr>
<th>Create a call</th>
<td><span class="bi-x-lg text-danger"></span></td>
<td><span class="bi-x-lg text-danger"></span></td>
<td><span class="bi-check-lg text-success"></span></td>
<td><span class="bi-x-lg text-danger"></span></td>
<td><span class="bi-check-lg text-success"></span></td>
</tr>

<tr>
<th>Edit a call</th>
<td><span class="bi-x-lg text-danger"></span></td>
<td><span class="bi-x-lg text-danger"></span></td>
<td><span class="bi-check-lg text-warning"></span> One's own</td>
<td><span class="bi-x-lg text-danger"></span></td>
<td><span class="bi-check-lg text-success"></span></td>
</tr>

<tr>
<th>Create a review</th>
<td><span class="bi-x-lg text-danger"></span></td>
<td><span class="bi-x-lg text-danger"></span></td>
<td><span class="bi-check-lg text-warning"></span> Any in call</td>
<td><span class="bi-x-lg text-danger"></span></td>
<td><span class="bi-check-lg text-success"></span></td>
</tr>

<tr>
<th>Edit a review</th>
<td><span class="bi-x-lg text-danger"></span></td>
<td><span class="bi-check-lg text-warning"></span> One's own</td>
<td><span class="bi-check-lg text-warning"></span> Any in call</td>
<td><span class="bi-x-lg text-danger"></span></td>
<td><span class="bi-check-lg text-success"></span></td>
</tr>

<tr>
<th>View a review</th>
<td><span class="bi-x-lg text-danger"></span></td>
<td><span class="bi-check-lg text-warning"></span> One's own</td>
<td><span class="bi-check-lg text-warning"></span> Any in call</td>
<td><span class="bi-check-lg text-success"></span></td>
<td><span class="bi-check-lg text-success"></span></td>
</tr>

<tr>
<th>Create a decision</th>
<td><span class="bi-x-lg text-danger"></span></td>
<td><span class="bi-check-lg text-warning"></span> Only chair</td>
<td><span class="bi-check-lg text-warning"></span> Any in call</td>
<td><span class="bi-x-lg text-danger"></span></td>
<td><span class="bi-check-lg text-success"></span></td>
</tr>

<tr>
<th>Edit a decision</th>
<td><span class="bi-x-lg text-danger"></span></td>
<td><span class="bi-check-lg text-warning"></span> Only chair</td>
<td><span class="bi-check-lg text-warning"></span> Any in call</td>
<td><span class="bi-x-lg text-danger"></span></td>
<td><span class="bi-check-lg text-success"></span></td>
</tr>

<tr>
<th>View a decision</th>
<td><span class="bi-check-lg text-warning"></span> One's own, when allowed</td>
<td><span class="bi-check-lg text-warning"></span> Only chair</td>
<td><span class="bi-check-lg text-warning"></span> Any in call</td>
<td><span class="bi-check-lg text-success"></span></td>
<td><span class="bi-check-lg text-success"></span></td>
</tr>

</table>
