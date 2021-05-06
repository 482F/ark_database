#### 必要ライブラリ
- PyMySQL


#### データベース構造
```
CREATE TABLE objects(
id INT UNIQUE AUTO_INCREMENT NOT NULL PRIMARY KEY,
name VARCHAR(200) UNIQUE NOT NULL,
max_stuck INT
);

CREATE TABLE recipes(
id INT UNIQUE AUTO_INCREMENT NOT NULL PRIMARY KEY,
product_id INT NOT NULL,
material_id INT NOT NULL,
material_required_number INT NOT NULL,
FOREIGN KEY(product_id) REFERENCES objects(id),
FOREIGN KEY(material_id) REFERENCES objects(id),
UNIQUE (product_id, material_id)
);
```
