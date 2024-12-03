



def test_insert_permissions_from_file():
    if len(get_all_files(cursor)) == 0:
        for f in ["a.txt", "b.txt", "c.txt"]:
            insert_file_mock(f"user@example.org/test2/{f}")


    yaml_string = """
    - permissions: read
    path: a.txt
    user: user@example.org
    
    - permissions: write
    path: b.txt
    user: user@example.org
    
    - permissions: write
    path: z.txt
    user: "*"
    type: disallow
    terminal: true
    """
    file_path = "user@example.org/test2/.syftperm"
    file = PermissionFile.from_string(yaml_string, file_path)


    set_rules_for_permfile(connection, file)

    assert len(get_all_file_mappings(cursor)) == 2



def test_overwrite_permissions_from_file():
    yaml_string = """
    - permissions: read
    path: a.txt
    user: user@example.org
    
    - permissions: write
    path: b.txt
    user: user@example.org
    
    - permissions: write
    path: z.txt
    user: "*"
    type: disallow
    terminal: true
    """
    file_path = "user@example.org/test2/.syftperm"
    file = PermissionFile.from_string(yaml_string, file_path)
    set_rules_for_permfile(connection, file)
    written_rules = get_rules_for_permfile(cursor, file)

    permissions = [x.permissions for x in written_rules]
    users = [x.user for x in written_rules]
    terminals = [x.terminal for x in written_rules]
    allows = [x.allow for x in written_rules]
    assert len(written_rules) == 3
    assert permissions == [[PermissionType.READ], [PermissionType.WRITE], [PermissionType.WRITE]]
    assert users == ["user@example.org", "user@example.org", "*"]
    assert terminals == [False, False, True]
    assert allows == [True, True, False]


    assert len([x for x in get_all_file_mappings(cursor) if x["permfile_path"] == str(file.filepath)]) == 2

    # overwrite
    yaml_string = """
    - permissions: read
    path: a.txt
    user: user@example.org
    
    - permissions: create
    path: x.txt
    user: user@example.org
    
    - permissions: create
    path: z.txt
    user: "*"
    type: disallow
    terminal: true
    
    - permissions: create
    path: d.txt
    user: "*"
    terminal: true
    """

    file_path = "user@example.org/test2/.syftperm"
    file = PermissionFile.from_string(yaml_string, file_path)
    set_rules_for_permfile(connection, file)
    new_existing_rules = get_rules_for_permfile(cursor, file)
    paths = [x.path for x in new_existing_rules]
    permissions = [x.permissions for x in new_existing_rules]
    users = [x.user for x in new_existing_rules]
    terminals = [x.terminal for x in new_existing_rules]
    allows = [x.allow for x in new_existing_rules]
    assert len(new_existing_rules) == 4
    assert paths == ["a.txt", "x.txt", "z.txt", "d.txt"]
    assert permissions == [[PermissionType.READ], [PermissionType.CREATE], [PermissionType.CREATE], [PermissionType.CREATE]]
    assert users == ["user@example.org", "user@example.org", "*", "*"]
    assert terminals == [False, False, True, True]
    assert allows == [True, True, False, True]
    assert len(get_all_file_mappings(cursor)) == 1




def test_computed_permissions():
    # TODO: split this and decouple db and permission overlaying
    computed_permission = ComputedPermission.from_user_and_path(cursor, "user@example.org", Path("user@example.org/test2/a.txt"))
    computed_permission.has_permission(PermissionType.READ)
    
    
    
    
def test_get_all_read_permissions_for_user():
    # Clear existing data
    cursor.execute("DELETE FROM file_metadata")
    cursor.execute("DELETE FROM rule_files") 
    cursor.execute("DELETE FROM rules")

    # Insert some example file metadata
    cursor.execute("""
    INSERT INTO file_metadata (id, path, hash, signature, file_size, last_modified) VALUES
        (1, 'user@example.org/test2/a.txt', 'hash1', 'signature1', 100, '2024-01-01'),
        (2, 'user@example.org/test2/b.txt', 'hash2', 'signature2', 200, '2024-01-02'),
        (3, 'user@example.org/test2/c.txt', 'hash3', 'signature3', 300, '2024-01-03')
    """)

    cursor.execute("""
    INSERT INTO rules (permfile_path, permfile_dir, priority, path, user, can_read, can_create, can_write, admin, disallow, terminal) VALUES
        ('user@example.org/test2/.syftperm', 'user@example.org/test2', 1, '*', '*', 1, 0, 0, 0, 0, 0),
        ('user@example.org/test2/.syftperm', 'user@example.org/test2', 2, '*', 'user@example.org', 0, 1, 1, 0, 0, 0),
        ('user@example.org/test2/.syftperm', 'user@example.org/test2', 3, '*', '*', 1, 1, 1, 0, 0, 0)

    """)

    # Insert example permission rules
    cursor.execute("""
    INSERT INTO rule_files (permfile_path, priority, file_id, match_for_email) VALUES
        ('user@example.org/test2/.syftperm', 1, 1, NULL),
        ('user@example.org/test2/.syftperm', 2, 2, NULL),
        ('user@example.org/test2/.syftperm', 3, 3, NULL)
    """)

    connection.commit()
    res = [dict(x) for x in get_read_permissions_for_user("user@example.org")]

    assert len(res) == 3
    assert res[0]["path"] == "user@example.org/test2/a.txt"
    assert res[0]["read_permission"] == True
    assert res[1]["path"] == "user@example.org/test2/b.txt"
    assert res[1]["read_permission"] == False
    assert res[2]["path"] == "user@example.org/test2/c.txt"
    assert res[2]["read_permission"] == True






