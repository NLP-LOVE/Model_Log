
drop table if exists project;
drop table if exists sub_model;
drop table if exists model_param;
drop table if exists model_metric;
drop table if exists best_result;


create table project
(
	project_id integer not null
		constraint model_pk
			primary key autoincrement,
	project_name text not null,
	project_remark text,
	nick_name text,
	create_time datetime not null,
	del_flag integer default 0 not null
);

create table model_metric
(
	metric_id integer not null
		constraint model_metric_pk
			primary key autoincrement,
	sub_model_id integer not null,
	metric_name text not null,
	metric_type text not null,
	epoch integer not null,
	metric_value float not null,
	create_time datetime not null
);

create table model_param
(
	param_id integer not null
		constraint model_param_pk
			primary key autoincrement,
	sub_model_id integer not null,
	param_type text not null,
	param_name text not null,
	param_value text not null,
	create_time datetime not null
);

create table sub_model
(
	sub_model_id integer not null
		constraint sub_model_pk
			primary key autoincrement,
	project_id integer not null,
	sub_model_sequence integer not null,
	sub_model_name text not null,
	sub_model_remark text,
	nick_name text,
	create_time datetime not null,
	del_flag integer default 0 not null
);

create table best_result
(
  best_result_id integer not null constraint best_result_pk primary key autoincrement,
  sub_model_id integer not null,
  best_name text not null,
  best_value float not null,
  best_epoch integer not null,
  create_time datetime not null
);

