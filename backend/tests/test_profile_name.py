def test_profile_name_is_shared_and_only_changes_the_current_account(client, db_session, auth_headers, users):
    admin,learner=users
    old_admin_name=admin.display_name
    response=client.patch('/api/auth/me',headers=auth_headers['learner'],json={'display_name':' Mon nouveau nom '})
    assert response.status_code==200,response.text
    assert response.json()['display_name']=='Mon nouveau nom'
    assert client.get('/api/auth/me',headers=auth_headers['learner']).json()['display_name']=='Mon nouveau nom'
    db_session.refresh(admin);db_session.refresh(learner)
    assert admin.display_name==old_admin_name
    assert learner.display_name=='Mon nouveau nom'
    assert client.patch('/api/auth/me',json={'display_name':'Forgé'}).status_code==401
    for value in ['   ',None]:
        assert client.patch('/api/auth/me',headers=auth_headers['learner'],json={'display_name':value}).status_code==400
    assert client.get('/api/auth/me',headers=auth_headers['learner']).json()['display_name']=='Mon nouveau nom'
