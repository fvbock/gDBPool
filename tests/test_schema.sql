CREATE TABLE test_values
(
  id serial NOT NULL,
	val1 integer NOT NULL,
	val2 integer NOT NULL,
  CONSTRAINT test_values_pkey PRIMARY KEY (id)
);

INSERT INTO test_values ( val1, val2 )
SELECT
  v1, v2
FROM
(
  SELECT generate_series( 1,1000000 ) as id, (random() * 9 + 1)::integer as v1, (random() * 99 + 1)::integer as v2
) foo;

-- DROP RULE notify_value_inserts ON test_values;

CREATE OR REPLACE RULE notify_value_inserts AS ON INSERT TO test_values
DO SELECT pg_notify( 'notify_test_values', 'id:' || NEW.id || '|val1:' || NEW.val1 || '|val2:' || NEW.val2 );

-- DROP RULE notify_value_updates ON test_values;

CREATE OR REPLACE RULE notify_value_updates AS ON UPDATE TO test_values
WHERE
  NEW.val1 <> OLD.val1
DO SELECT pg_notify( 'notify_test_values', 'id:' || NEW.id || '|val1:' || NEW.val1 );
