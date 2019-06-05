create table blacklists
(
    username     text not null,
    invites_sent text,
    timestamp    text,
    task_id      text
        constraint blacklists_taskid
            unique
);

create index blacklists_username_index
    on blacklists (username);

create table codes
(
    email   text
        primary key
        unique,
    results text,
    headers text,
    cookies text
);

create table tasks
(
    task_id   text not null
        constraint tasks_pk
            primary key,
    timestamp text not null,
    username  text,
    type      text,
    state     int default 0 not null
);

create unique index tasks_task_id_uindex
    on tasks (task_id);

create table user
(
    email        text
        primary key
        unique,
    cookies      text,
    date         text not null,
    login_date   text default null,
    latest_proxy text default null,
    info         text
);

