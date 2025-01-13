## Highlights

### Textual UI

In this release we have started experimenting with new ways to improve the user experience as we are aware the main
blocker for most people to use our library is a trustworthy interface. 

The first step in this regard is a GUI using [Textual](https://textual.textualize.io/) which will have all the information
you might need as a `SyftBox` user (Logs, Tutorials, APIs, FileSystem and more), neatly organized and easily accessible. 

You can try it by running the following command:

```
syftbox tui --config path/to/syftbox/config.json
```

You need to clone our repo and have a client already running. Here is a preview in case you are not convinced yet:

<img src="assets/tui_example.png" alt="drawing" width="1280"/>

If you have any suggestion on how we can improve it or on what you are expecting it to allow users to do, we are open to
new ideas. You can help us either by sending us a [slack message](https://openmined.slack.com/ssb/redirect) or by opening a [Github issue](https://github.com/OpenMined/syft/issues).

### Permisssions

We have updated our way of dealing with permissions in order to allow for better user control. If you checked your 
datasite's folder after updating, you will probably already have noticed you have a `syftperm.yaml` file instead of the
legacy `_.syftperm`. Here is a comparision between the two of them:

<div style="display: flex; gap: 20px;">

  <div style="flex: 1;">
    <strong>_.syftperm:</strong>
    <pre>{
    "admin": ["teodor@openmined.org"], 
    "read": ["teodor@openmined.org"], 
    "write": ["teodor@openmined.org"], 
    "filepath": "/home/teo/Desktop/SyftBox/teodor@openmined.org/_.syftperm", 
    "terminal": false
}
    </pre>
  </div>

  <div style="flex: 1;">
    <strong>syftperm.yaml:</strong>
    <pre>
- path: '**'
    permissions:
    - admin
    - create
    - write
    - read
    user: teodor@openmined.org
  </pre>
  </div></div>

As you can see we have new rule based-permissions that allow an owner of a `SyftBox` to define
which users can access their files. These new rules will help use scale our infrastructure
and improve requests response time while providing greater clarity for the users over access rights.

If you want to read more on these changes, please consult: [this document](permissions.md) 

### Breaking Changes

With the new permissions update, you will need to update your apps making the following change when trying to access
the permission for a client:

```diff
- permission = SyftPermission.mine_with_public_write(client.email)
+ permission = SyftPermission.mine_with_public_write(context=client, dir=path)
```

Ignoring this change will break any app you have already developed so please take note.


## What's Changed
* prepare sync plugin for dashboard by @eelcovdw in https://github.com/OpenMined/syft/pull/440
* Cleanup sync and log sync status locally by @eelcovdw in https://github.com/OpenMined/syft/pull/443
* Fix flaky e2e test by @khoaguin in https://github.com/OpenMined/syft/pull/448
* add path alias for file_path in LocalState by @shubham3121 in https://github.com/OpenMined/syft/pull/452
* Check client version on startup + log user OS to analytics by @eelcovdw in https://github.com/OpenMined/syft/pull/451
* sync dashboard by @eelcovdw in https://github.com/OpenMined/syft/pull/404
* revert localstate path by @eelcovdw in https://github.com/OpenMined/syft/pull/454
* Fix symlink race condition by @eelcovdw in https://github.com/OpenMined/syft/pull/453
* change model arch filename by @shubham3121 in https://github.com/OpenMined/syft/pull/459
* fix client shutdown by @abyesilyurt in https://github.com/OpenMined/syft/pull/457
* Remove git as a dependency for the starter_app by @abyesilyurt in https://github.com/OpenMined/syft/pull/458
* refactor sync endpoints by @eelcovdw in https://github.com/OpenMined/syft/pull/460
* [ci] temporarily disable fl model training by @rasswanth-s in https://github.com/OpenMined/syft/pull/464
* enable globstar and fill permission tables in db init by @abyesilyurt in https://github.com/OpenMined/syft/pull/462
* Add permission + rejection logic to Consumer by @eelcovdw in https://github.com/OpenMined/syft/pull/465
* ADD cpu_tracker as a default app by @IonesioJunior in https://github.com/OpenMined/syft/pull/466
* permission integration tests by @eelcovdw in https://github.com/OpenMined/syft/pull/469
* Added Computed Permissions tests by @teo-milea in https://github.com/OpenMined/syft/pull/471
* Removing terminal permissions by @teo-milea in https://github.com/OpenMined/syft/pull/472
* cleanup repo by @yashgorana in https://github.com/OpenMined/syft/pull/475
* Bump pyjwt from 2.10.0 to 2.10.1 by @dependabot in https://github.com/OpenMined/syft/pull/477
* Bump python-multipart from 0.0.12 to 0.0.19 by @dependabot in https://github.com/OpenMined/syft/pull/476
* pin new versions by @yashgorana in https://github.com/OpenMined/syft/pull/478
* Configure Renovate by @renovate in https://github.com/OpenMined/syft/pull/479
* Test Renovate by @rasswanth-s in https://github.com/OpenMined/syft/pull/483
* Update astral-sh/setup-uv action to v4 by @renovate in https://github.com/OpenMined/syft/pull/480
* Update dcarbone/install-jq-action action to v3 by @renovate in https://github.com/OpenMined/syft/pull/481
* update renovate schema by @rasswanth-s in https://github.com/OpenMined/syft/pull/486
* Lock file maintenance by @renovate in https://github.com/OpenMined/syft/pull/488
* Update dependency pyjwt to v2.10.1 [SECURITY] by @renovate in https://github.com/OpenMined/syft/pull/489
* permissions implementation by @koenvanderveen in https://github.com/OpenMined/syft/pull/397
* migration fix by @koenvanderveen in https://github.com/OpenMined/syft/pull/490
* fix staging issues by @eelcovdw in https://github.com/OpenMined/syft/pull/491
* fix logic by @koenvanderveen in https://github.com/OpenMined/syft/pull/492
* fix public write method by @koenvanderveen in https://github.com/OpenMined/syft/pull/493
* add permission method by @koenvanderveen in https://github.com/OpenMined/syft/pull/494
* FastAPI OTEL instrumentation by @khoaguin in https://github.com/OpenMined/syft/pull/468
* OTEL disabled by default by @yashgorana in https://github.com/OpenMined/syft/pull/496
* Fix perm factory methods by @eelcovdw in https://github.com/OpenMined/syft/pull/497
* Telemetry: Add OS name, version and arch attributes by @khoaguin in https://github.com/OpenMined/syft/pull/495
* update save by @abyesilyurt in https://github.com/OpenMined/syft/pull/499
* migrate + gunicorn by @yashgorana in https://github.com/OpenMined/syft/pull/500
* Migrate before running the server by @eelcovdw in https://github.com/OpenMined/syft/pull/498
* move to hatchling + leaner builds by @yashgorana in https://github.com/OpenMined/syft/pull/503
* Sync Benchmark Metrics by @shubham3121 in https://github.com/OpenMined/syft/pull/504
* rename clientside components, add client for server communication by @eelcovdw in https://github.com/OpenMined/syft/pull/467
* add streaming bulk downloads by @abyesilyurt in https://github.com/OpenMined/syft/pull/507
* Enable mypy by @khoaguin in https://github.com/OpenMined/syft/pull/419
* Benchmark Report by @shubham3121 in https://github.com/OpenMined/syft/pull/463
* Server Request Size Limit by @rasswanth-s in https://github.com/OpenMined/syft/pull/512
* track user geo location of the client user by @shubham3121 in https://github.com/OpenMined/syft/pull/514
* Textual TUI prototype by @eelcovdw in https://github.com/OpenMined/syft/pull/508
* staging fix by @eelcovdw in https://github.com/OpenMined/syft/pull/519

**Full Changelog**: https://github.com/OpenMined/syft/compare/0.2.11...0.2.12


